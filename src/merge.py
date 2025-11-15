import msgspec
import pandas as pd
import numpy as np
import string
from bpm import get_multiplier


def match_frequency_to_char(interval_list, freq_dict):
    # Sort interval_list by score in descending order to prioritize high-scoring characters
    sorted_intervals = sorted(
        interval_list, key=lambda x: (x["start"], x["score"]), reverse=False
    )

    # Sort frequency dictionary by confidence in descending order
    # Assuming freq_dict has 'time', 'freq', and 'confidence' keys
    freq_sorted = sorted(
        zip(freq_dict["time"], freq_dict["freq"], freq_dict["confidence"]),
        key=lambda x: x[2],
        reverse=True,
    )

    result = []
    for interval in sorted_intervals:
        # Find the best matching frequency
        best_match = None
        for time, freq, confidence in freq_sorted:
            # Check if the frequency time falls within the interval
            if interval["start"] <= time <= interval["end"]:
                best_match = {
                    "start": time,
                    "duration": interval["end"] - interval["start"],
                    "pitch": freq,
                    "char": interval["char"],
                }
                break  # Take the first (highest confidence) match

        if best_match:
            result.append(best_match)

    return result


def fix_missing(words):
    for x, w in enumerate(words):
        if "start" not in w:
            if x == 0:
                w["start"] = 0
                w["end"] = 0
            else:
                w["start"] = words[x - 1]["end"]
            if w["char"] == " ":
                w["char"] == "--"
        if "end" not in w:
            w["end"] = words[x - 1]["end"]
        if "score" not in w:
            w["score"] = 0


def match_pitch(words, frequencies):
    fix_missing(words)

    # words = [w for w in words if len(w) > 1]
    result = match_frequency_to_char(words, frequencies)
    return pd.DataFrame(result)


class NoteCollection(msgspec.Struct):
    chars: pd.DataFrame
    freqs: pd.DataFrame
    result: pd.DataFrame = None

    def __post_init__(self):
        self.result = match_pitch(self.chars, self.freqs)

    def print(self, debug: bool = False):
        with open("notes.txt", "w", newline="", encoding="utf-8") as file:
            file.writelines(
                (
                    f": {row[0]:.2f} {row[1]:.2f} {row[2]:.2f} {row[3]}\n"
                    if debug
                    else f": {row[0]:.0f} {row[1]:.0f} {row[2]:.0f} {row[3]}\n"
                )
                if row[3] != "--"
                else (f"- {row[0]:.2f}\n" if debug else f"- {row[0]:.0f}\n")
                for row in self.result.to_numpy()
            )

    def normalize_duration(self):
        self.result["next_start"] = self.result["start"].shift(-1)
        self.result["duration"] = self.result.apply(
            lambda x: x["next_start"] - x["start"]
            if x["start"] + x["duration"] > x["next_start"]
            else x["duration"],
            axis=1,
        )
        return self

    def running_bag(self):
        punc_breaks = {"?", "!", ":", ".", '"'}
        sentence = ""
        running = []

        for x, row in self.result.iterrows():
            _add = False
            char: str = row["char"]
            if char.isupper():
                running.append(sentence)
                sentence = ""
                _add = True
            sentence += char
            if char[-1] in punc_breaks:
                running.append(sentence)
                sentence = ""
                _add = True
            if not _add:
                running.append(sentence)
        self.result["running"] = running
        self.result["previous_running"] = self.result["running"].shift(1)
        self.result["finished_sentence"] = self.result.apply(
            lambda x: x["running"] == x["previous_running"], axis=1
        )
        rows = []
        for x, row in self.result.iterrows():
            if row["finished_sentence"]:
                br = {
                    "start": row["start"],
                    "duration": 100,
                    "pitch": np.nan,
                    "char": "--",
                }
                rows.append(pd.Series(br))
            rows.append(row[["start", "duration", "pitch", "char"]])

        new = pd.DataFrame(rows).reset_index(drop=True)
        self.result = new
        return self

    def insert_breaks(self):
        """Inserts break note (char = '-') if gap > threshold between consecutive notes"""
        threshold = 0.5
        if self.result is None or len(self.result) == 0:
            return self
        punc_breaks = set(["?", "!", ":", ".", '"', " "])
        df = self.result.copy().reset_index(drop=True)

        # compute end times and subsequent gap
        df["end"] = df["start"] + df["duration"]
        gaps = df["start"].shift(-1) - df["end"]
        gaps = gaps.fillna(0)

        rows = []
        for i, row in df.iterrows():
            start = None
            if (
                i != 0
                and row["char"][0].isupper()
                and row["char"][0] != "I"
                and rows[-1]["char"] != "--"
            ):
                start = row["start"] - 0.01
                br = {
                    "start": start,
                    "duration": 100,
                    "pitch": np.nan,
                    "char": "--",
                }
                rows.append(pd.Series(br))
            rows.append(row[["start", "duration", "pitch", "char"]])
            # sentence += row["char"]
            # if len(sentence.split(" ")) >= 5 and sentence[-1] in punc_breaks:
            #    print("Sentence: %s", sentence)
            #    start = row["end"]
            #    sentence = ""

            # if start:
            #    continue
            gap = gaps.iat[i]
            ch = str(row["char"])

            if ch[-1] in punc_breaks and rows[-1]["char"] != "--" and gap > threshold:
                start = row["end"]
            # insert break note: start at end, duration = gap, pitch = NaN, char = '-'
            if start:
                br = {
                    "start": start,
                    "duration": gap,
                    "pitch": np.nan,
                    "char": "--",
                }
                rows.append(pd.Series(br))

        new = pd.DataFrame(rows).reset_index(drop=True)
        # sort just in case and reindex
        new = (
            new[["start", "duration", "pitch", "char"]]
            .sort_values("start")
            .reset_index(drop=True)
        )
        self.result = new
        return self

    def merge_chars(self):
        """Merges chars in consecutive notes if they have the same pitch and previous char does not end with a space char"""
        if self.result is None or len(self.result) == 0:
            return self

        self.result["previous_pitch"] = self.result["pitch"].shift(1)
        self.result["previous_char"] = self.result["char"].shift(1)
        self.result["can_extend"] = self.result.apply(
            lambda x: (x["previous_char"] and not x["previous_char"].endswith(" "))
            and x["char"] != "--"
            and round(x["pitch"] if not pd.isna(x["pitch"]) else 0)
            == round(x["previous_pitch"] if not pd.isna(x["previous_pitch"]) else 0),
            axis=1,
        )
        merged = []
        for _, row in self.result.iterrows():
            if not merged or not row["can_extend"]:
                merged.append(row.to_dict())
                continue
            prev = merged[-1]
            prev_char = str(prev["char"])
            print(prev_char, "+", row["char"])
            prev["char"] = prev_char + str(row["char"])

            # new duration: max end - prev start
            prev_end = prev["start"] + prev["duration"]
            row_end = row["start"] + row["duration"]
            new_end = max(prev_end, row_end)
            prev["duration"] = new_end - prev["start"]

            merged[-1] = prev

        self.result = pd.DataFrame(merged)[
            ["start", "duration", "pitch", "char"]
        ].reset_index(drop=True)
        return self

    def merge_chars_old(self):
        df = self.result.copy().reset_index(drop=True)

        merged = []
        for i, row in df.iterrows():
            if not merged:
                merged.append(row.to_dict())
                continue
            prev = merged[-1]
            same_pitch = (pd.isna(prev["pitch"]) and pd.isna(row["pitch"])) or (
                prev["pitch"] == row["pitch"]
            )
            prev_char = str(prev["char"])
            # only merge if same pitch, previous char does NOT end with a space and neither is a break '-'
            if (
                same_pitch
                and (not prev_char.endswith(" "))
                and (prev_char != "--")
                and (row["char"] != "--")
            ):
                # concatenate chars and extend duration to cover through this note's end
                prev["char"] = prev_char + str(row["char"])
                # new duration: max end - prev start
                prev_end = prev["start"] + prev["duration"]
                row_end = row["start"] + row["duration"]
                new_end = max(prev_end, row_end)
                prev["duration"] = new_end - prev["start"]
                merged[-1] = prev
            else:
                merged.append(row.to_dict())

        new = pd.DataFrame(merged)[["start", "duration", "pitch", "char"]].reset_index(
            drop=True
        )
        self.result = new
        return self

    def merge_spaces(self):
        """Append space to previous char. Discards space pitch and duration"""
        if self.result is None or len(self.result) == 0:
            return self

        df = self.result.copy().reset_index(drop=True)
        kept = []
        i = 0
        while i < len(df):
            row = df.iloc[i].to_dict()
            if str(row["char"]) == " ":
                # attach to previous if exists
                if kept:
                    kept[-1]["char"] = str(kept[-1]["char"]) + " "
                    # extend previous duration to include this space duration if needed
                    prev_end = kept[-1]["start"] + kept[-1]["duration"]
                    space_end = row["start"] + row["duration"]
                    if space_end > prev_end:
                        kept[-1]["duration"] = space_end - kept[-1]["start"]
                # discard the space row (do not append)
            else:
                kept.append(row)
            i += 1

        new = pd.DataFrame(kept)[["start", "duration", "pitch", "char"]].reset_index(
            drop=True
        )
        self.result = new
        return self

    def merge_punctuation(self):
        """Append punctuation to previous char. Discards punctuation pitch and duration"""
        if self.result is None or len(self.result) == 0:
            return self

        punctuation = set(string.punctuation)
        df = self.result.copy().reset_index(drop=True)
        kept = []
        for _, r in df.iterrows():
            row = r.to_dict()
            ch = str(row["char"])
            # treat single-character punctuation only
            if len(ch) == 1 and ch in punctuation:
                if kept:
                    kept_prev = kept[-1]
                    kept_prev["char"] = str(kept_prev["char"]) + ch
                    prev_end = kept_prev["start"] + kept_prev["duration"]
                    punc_end = row["start"] + row["duration"]
                    if punc_end > prev_end:
                        kept_prev["duration"] = punc_end - kept_prev["start"]
                    kept[-1] = kept_prev
                # else: nothing to attach to — drop punctuation
            else:
                kept.append(row)
        new = pd.DataFrame(kept)[["start", "duration", "pitch", "char"]].reset_index(
            drop=True
        )
        self.result = new
        return self

    def apply_bpm(self, BPM: float):
        ubpm = BPM / 4
        m = get_multiplier(ubpm)
        ubpm *= m
        print("BPM:", ubpm, m)

        self.result["start"] *= m * BPM / 60
        self.result["duration"] *= m * BPM / 60

        return self
