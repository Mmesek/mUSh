import pandas as pd
import json
import numpy as np
import string

# with open("t.json", "r", newline="", encoding="utf-8") as file:
#    raw_chars = json.load(file)
#
# chars = pd.DataFrame(raw_chars).fillna(0)
# with open("p.json", "r", newline="", encoding="utf-8") as file:
#    f = json.load(file)
# freqs = pd.DataFrame(f)


def match_pitch(words, frequencies):
    intervals = pd.IntervalIndex.from_arrays(
        words["start"], words["end"], closed="left"
    )
    idx = intervals.get_indexer(frequencies["time"])
    freqs = frequencies.copy()
    freqs["char_idx"] = idx
    freqs = freqs[freqs["char_idx"] != -1]  # drop outside intervals
    # event_times = freqs.groupby("char_idx")["time"].min().to_numpy()

    # group by char index to compute representative pitch
    grouped = freqs.groupby("char_idx")["freq"]
    agg = grouped.agg(
        pitch_median="median", pitch_mean="mean", pitch_max="max", count="size"
    ).reset_index()

    # join back to chars (preserve original order)
    chars_with_pitch = chars.reset_index(drop=True).merge(
        agg, left_index=True, right_on="char_idx", how="left"
    )

    # build final array: start, duration, pitch, character
    # choose pitch rule here: use median (fallback to NaN if no samples)
    chars_with_pitch["duration"] = chars_with_pitch["end"] - chars_with_pitch["start"]
    chars_with_pitch["pitch"] = chars_with_pitch[
        "pitch_median"
    ]  # change to pitch_mean or pitch_max if desired

    result = chars_with_pitch[["start", "duration", "pitch", "char"]].dropna()
    result["pitch"] = result["pitch"].astype(int)

    # convert to numpy array if needed
    # result_array = result.to_numpy()

    # result and result_array available
    # result, result_array
    # iois = np.diff(result["start"])
    # BPM = 60 / np.median(iois)
    # BPM = 153
    # print("BPM:", BPM)
    # BPS = BPM / 60
    # result["start"] *= BPS
    # result["duration"] *= BPS
    return result


def insert_breaks(result):
    threshold = 0.8  # gap threshold

    # ensure sorted
    res = result.sort_values("start").reset_index(drop=True).copy()

    # compute next start and gap
    res["next_start"] = res["start"].shift(-1)
    res["gap"] = res["next_start"] - (res["start"] + res["duration"])

    # rows where gap > threshold
    gaps = res[res["gap"] > threshold].copy()

    # build list of new rows: original rows plus inserted blank rows after each gap
    out_rows = []
    for i, row in res.iterrows():
        out_rows.append(row[["start", "duration", "pitch", "char"]].to_dict())
        if row["gap"] > threshold:
            gap_start = row["start"] + row["duration"]
            gap_duration = row["gap"]
            out_rows.append(
                {
                    "start": gap_start,
                    "duration": gap_duration,
                    "pitch": np.nan,
                    "char": "--",
                }
            )

    # final DataFrame
    out = pd.DataFrame(out_rows)[["start", "duration", "pitch", "char"]].reset_index(
        drop=True
    )

    return out


def merge_same(out):
    df = out.reset_index(drop=True).copy()

    # define keys for equality; treat floats with tolerance if needed
    # here we keep exact equality for char and pitch; to tolerate numeric fuzz use np.isclose
    df["char_key"] = df["char"]
    df["pitch_key"] = df["pitch"]

    # create run id when either key changes
    change = (df["char_key"] != df["char_key"].shift(1)) | (
        df["pitch_key"] != df["pitch_key"].shift(1)
    )
    df["run"] = change.cumsum()

    # aggregate runs
    merged = df.groupby("run", as_index=False).agg(
        {
            "start": "first",
            "duration": "sum",  # merge durations
            "pitch": "first",  # same across run
            "char": "first",  # same across run
        }
    )[["start", "duration", "pitch", "char"]]

    return merged


def merge_same2(df: pd.DataFrame):
    df = df.reset_index(drop=True).copy()

    # numeric tolerance for pitch equality (set 0 for exact)
    tol = 0  # 1e-9
    df["pitch"] = df["pitch"].dropna().astype(int)

    # helper to compare pitches with NaNs: treat NaN != anything (won't merge blanks)
    prev_pitch = df["pitch"].shift(1)
    same_pitch = (
        (~df["pitch"].isna())
        & (~prev_pitch.isna())
        & (np.isclose(df["pitch"], prev_pitch, atol=tol))
    )

    # start a new run when pitch differs (we ignore char differences)
    new_run = ~same_pitch
    run_id = new_run.cumsum()

    # aggregate: for char we concatenate adjacent different characters (you can choose sep)
    agg = (
        df.groupby(run_id, sort=False)
        .agg(
            {
                "start": "first",
                "duration": "sum",
                "pitch": "first",
                "char": lambda s: "".join(
                    s.dropna().astype(str)
                ),  # change to ' '.join or other rule
            }
        )
        .reset_index(drop=True)
    )

    return agg


from functools import reduce


def append_if_prev_not_space(series):
    def reducer(acc, nxt):
        if pd.isna(nxt):
            return acc
        nxt = str(nxt)
        if acc == "":
            return nxt
        return (
            acc + nxt if acc[-1] != " " else acc + ""
        )  # skip appending if previous is space

    return reduce(reducer, series.dropna().astype(str), "")


def merge_same3(df: pd.DataFrame):
    df = df.reset_index(drop=True).copy()

    # numeric tolerance for pitch equality (set 0 for exact)
    tol = 0  # 1e-9
    df["pitch"] = df["pitch"].dropna().astype(int)

    # helper to compare pitches with NaNs: treat NaN != anything (won't merge blanks)
    prev_pitch = df["pitch"].shift(1)
    same_pitch = (
        (~df["pitch"].isna())
        & (~prev_pitch.isna())
        & (np.isclose(df["pitch"], prev_pitch, atol=tol))
    )

    # start a new run when pitch differs (we ignore char differences)
    new_run = ~same_pitch
    run_id = new_run.cumsum()
    agg = (
        df.groupby(run_id, sort=False)
        .agg(
            {
                "start": "first",
                "duration": "sum",
                "pitch": "first",
                "char": append_if_prev_not_space,
            }
        )
        .reset_index(drop=True)
    )
    return agg


def merge_spaces(df: pd.DataFrame):
    tol = 0
    chars = df["char"].astype(object).fillna("")  # keep original indexing
    is_space = chars == " "

    # compute same_pitch and new_run as you already do, then run_id:
    prev_pitch = df["pitch"].shift(1)
    same_pitch = (
        (~df["pitch"].isna())
        & (~prev_pitch.isna())
        & (np.isclose(df["pitch"], prev_pitch, atol=tol))
    )
    new_run = ~same_pitch
    run_id = new_run.cumsum()

    # for space rows, if not the first row, set run_id to previous run_id
    run_id = run_id.copy()
    run_id[is_space & (run_id.index != 0)] = run_id.shift(1)[
        is_space & (run_id.index != 0)
    ]

    agg = (
        df.groupby(run_id, sort=False)
        .agg(
            start=("start", "first"),
            duration=("duration", "sum"),
            pitch=("pitch", "first"),
            char=("char", lambda s: "".join(s.dropna().astype(str))),
        )
        .reset_index(drop=True)
    )
    return agg


def append_space_to_prev(df: pd.DataFrame, char_col="char") -> pd.DataFrame:
    """
    For each row where df[char_col] == " ", append a single space to the previous non-NaN/empty char
    and drop the space rows. Preserves start/duration/pitch of the previous row.
    Returns a new DataFrame with indices reset.
    """
    df = df.copy().reset_index(drop=True)
    mask_space = df[char_col] == " "
    for i in df.index[mask_space]:
        # find previous row to attach to
        prev = i - 1
        while prev >= 0 and pd.isna(df.at[prev, char_col]):
            prev -= 1
        if prev >= 0:
            prev_val = df.at[prev, char_col]
            # treat empty string as valid value to append to
            df.at[prev, char_col] = ("" if pd.isna(prev_val) else str(prev_val)) + " "
    return df.loc[~mask_space].reset_index(drop=True)


def print_notes(array: np.ndarray, debug: bool = False):
    with open("notes.txt", "w", newline="", encoding="utf-8") as file:
        file.writelines(
            (
                f": {row[0]:.2f} {row[1]:.2f} {row[2]:.2f} {row[3]}\n"
                if debug
                else f": {row[0]:.0f} {row[1]:.0f} {row[2]:.0f} {row[3]}\n"
            )
            if row[3] != "--"
            else (f"- {row[0]:.2f}\n" if debug else f"- {row[0]:.0f}\n")
            for row in array
        )


import msgspec


class NoteCollection(msgspec.Struct):
    chars: pd.DataFrame
    freqs: pd.DataFrame
    result: pd.DataFrame = None
    """Contains 4 columns: `start`, `duration`, `pitch`, `char`"""

    def __post_init__(self):
        self.result = match_pitch(self.chars, self.freqs)

    def set_gap(self):
        """Sets gap and decreases `start` vector by gap value"""
        print("GAP:", self.result["start"][0])
        self.result["start"] -= self.result["start"][0]
        return self

    def print(self, debug: bool = False):
        print_notes(self.result.to_numpy(), debug)

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
        punc_breaks = set(["?", "!", ":", ".", '"'])
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
                start = rows[-1]["start"] + rows[-1]["duration"] - 0.02
                br = {
                    "start": start,
                    "duration": 100,
                    "pitch": np.nan,
                    "char": "--",
                }
                rows.append(pd.Series(br))
            rows.append(row[["start", "duration", "pitch", "char"]])
            if start:
                continue
            gap = gaps.iat[i]
            ch = str(row["char"])

            if (
                ch[-1] in punc_breaks
                or (len(ch) > 1 and ch[-2] in punc_breaks)
                or gap > threshold
            ):
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


def get_multiplier(real_bpm: float) -> int:
    """Calculates the multiplier for the BPM"""

    if real_bpm == 0:
        raise Exception("BPM is 0")

    multiplier = 1
    result = 0
    while result < 400:
        result = real_bpm * multiplier
        multiplier += 1
    return multiplier - 2


# (
#    NoteCollection(chars, freqs)
#    .set_gap()
#    .apply_bpm(129.19)
#    .merge_punctuation()
#    .merge_spaces()
#    .merge_chars()
#    .insert_breaks()  #
#    .print(debug=False)
# )
