
import pandas as pd
from pybaseball import statcast


# Settings
start_date = "2026-04-01"
end_date = "2026-04-30"
pitcher_name = "Soriano, José"


# Download Statcast data
print("Downloading Statcast data...")

data = statcast(
    start_dt=start_date,
    end_dt=end_date
)


# Filter for the pitcher
pitcher_data = data[
    data["player_name"] == pitcher_name
].copy()

pitcher_data = pitcher_data.dropna(
    subset=["pitch_name"]
)

# Identify batter handedness
pitcher_data["batter_hand"] = pitcher_data["stand"].map({
    "R": "RHB",
    "L": "LHB"
})

# Sort pitches so we can track pitch sequences
pitcher_data = pitcher_data.sort_values(
    ["game_pk", "at_bat_number", "pitch_number"]
).copy()

# Create the count before each pitch
pitcher_data["count"] = (
    pitcher_data["balls"].astype(str)
    + "-"
    + pitcher_data["strikes"].astype(str)
)

# Identify the previous pitch within each plate appearance
pitcher_data["previous_pitch"] = (
    pitcher_data
    .groupby(["game_pk", "at_bat_number"])["pitch_name"]
    .shift(1)
)


# Swing and miss indicators
swing_descriptions = [
    "swinging_strike",
    "swinging_strike_blocked",
    "foul",
    "foul_tip",
    "hit_into_play",
    "hit_into_play_no_out",
    "hit_into_play_score",
    "foul_bunt",
    "missed_bunt"
]

whiff_descriptions = [
    "swinging_strike",
    "swinging_strike_blocked",
    "missed_bunt"
]

pitcher_data["swing"] = pitcher_data["description"].isin(
    swing_descriptions
)

pitcher_data["whiff"] = pitcher_data["description"].isin(
    whiff_descriptions
)

pitcher_data["called_strike"] = (
    pitcher_data["description"] == "called_strike"
)

pitcher_data["csw"] = (
    pitcher_data["called_strike"] | pitcher_data["whiff"]
)


# Identify plate appearance outcomes
pitcher_data["pa_ending_pitch"] = pitcher_data["events"].notna()

pitcher_data["batted_ball"] = pitcher_data["launch_speed"].notna()

hit_events = ["single", "double", "triple", "home_run"]

pitcher_data["hit"] = pitcher_data["events"].isin(hit_events)

non_at_bat_events = [
    "walk",
    "intent_walk",
    "hit_by_pitch",
    "sac_bunt",
    "sac_fly",
    "catcher_interf"
]

pitcher_data["at_bat"] = (
    pitcher_data["pa_ending_pitch"]
    & ~pitcher_data["events"].isin(non_at_bat_events)
)


# Calculate total bases
pitcher_data["total_bases"] = 0

base_values = {
    "single": 1,
    "double": 2,
    "triple": 3,
    "home_run": 4
}

for event, bases in base_values.items():
    pitcher_data.loc[
        pitcher_data["events"] == event,
        "total_bases"
    ] = bases


# Identify hard-hit balls
pitcher_data["hard_hit"] = (
    pitcher_data["launch_speed"] >= 95
)


# Estimate barrels using exit velocity and launch angle
def is_barrel(row):
    exit_velocity = row["launch_speed"]
    launch_angle = row["launch_angle"]

    if pd.isna(exit_velocity) or pd.isna(launch_angle):
        return False

    if exit_velocity < 98:
        return False

    if exit_velocity >= 116:
        return True

    lower_angle = 26 - (116 - exit_velocity) * 0.32
    upper_angle = 30 + (116 - exit_velocity) * 0.32

    return lower_angle <= launch_angle <= upper_angle


pitcher_data["barrel"] = pitcher_data.apply(
    is_barrel,
    axis=1
)


# Summarize pitch usage and performance by handedness and count
pitch_counts = (
    pitcher_data
    .dropna(subset=["batter_hand"])
    .groupby(["batter_hand", "count", "pitch_name"])
    .agg(
        pitches=("pitch_name", "size"),
        average_velocity=("release_speed", "mean"),
        swings=("swing", "sum"),
        whiffs=("whiff", "sum"),
        called_strikes=("called_strike", "sum"),
        csw=("csw", "sum"),
        plate_appearances=("pa_ending_pitch", "sum"),
        hits=("hit", "sum"),
        at_bats=("at_bat", "sum"),
        total_bases=("total_bases", "sum"),
        xwOBA=("estimated_woba_using_speedangle", "mean"),
        wOBA_value=("woba_value", "sum"),
        batted_balls=("batted_ball", "sum"),
        hard_hit=("hard_hit", "sum"),
        barrels=("barrel", "sum")
    )
    .reset_index()
)


# Calculate usage within each handedness and count
total_by_count = (
    pitcher_data
    .dropna(subset=["batter_hand"])
    .groupby(["batter_hand", "count"])
    .size()
    .reset_index(name="total_pitches")
)

pitch_counts = pitch_counts.merge(
    total_by_count,
    on=["batter_hand", "count"]
)

pitch_counts["usage"] = (
    pitch_counts["pitches"]
    / pitch_counts["total_pitches"]
    * 100
)

pitch_counts["whiff_rate"] = (
    pitch_counts["whiffs"]
    / pitch_counts["swings"].replace(0, float("nan"))
    * 100
)

pitch_counts["CSW%"] = (
    pitch_counts["csw"]
    / pitch_counts["pitches"]
    * 100
)

pitch_counts["wOBA"] = (
    pitch_counts["wOBA_value"]
    / pitch_counts["plate_appearances"].replace(0, float("nan"))
)

pitch_counts["BA"] = (
    pitch_counts["hits"]
    / pitch_counts["at_bats"].replace(0, float("nan"))
)

pitch_counts["SLG"] = (
    pitch_counts["total_bases"]
    / pitch_counts["at_bats"].replace(0, float("nan"))
)

pitch_counts["HardHit%"] = (
    pitch_counts["hard_hit"]
    / pitch_counts["batted_balls"].replace(0, float("nan"))
    * 100
)

pitch_counts["Barrel%"] = (
    pitch_counts["barrels"]
    / pitch_counts["batted_balls"].replace(0, float("nan"))
    * 100
)


# Round the results for easier reading
rounding = {
    "usage": 1,
    "average_velocity": 1,
    "whiff_rate": 1,
    "CSW%": 1,
    "xwOBA": 3,
    "wOBA": 3,
    "BA": 3,
    "SLG": 3,
    "HardHit%": 1,
    "Barrel%": 1
}

pitch_counts = pitch_counts.round(rounding)


# Print report heading
print("\n")
print("=" * 65)
print("PITCHER:", pitcher_name)
print("DATE RANGE:", start_date, "to", end_date)
print("TOTAL PITCHES:", len(pitcher_data))
print("=" * 65)


# Pitch selection by count
for hand in ["RHB", "LHB"]:

    print("\n")
    print("=" * 65)
    print("PITCH SELECTION VS", hand)
    print("=" * 65)

    selection = pitch_counts[
        pitch_counts["batter_hand"] == hand
    ][
        [
            "count",
            "pitch_name",
            "pitches",
            "usage"
        ]
    ].copy()

    selection = selection.sort_values(
        ["count", "usage"],
        ascending=[True, False]
    )

    print(selection.to_string(index=False))


# Pitch performance by count
for hand in ["RHB", "LHB"]:

    print("\n")
    print("=" * 65)
    print("PITCH PERFORMANCE VS", hand)
    print("=" * 65)

    performance = pitch_counts[
        pitch_counts["batter_hand"] == hand
    ][
        [
            "count",
            "pitch_name",
            "usage",
            "average_velocity",
            "swings",
            "whiffs",
            "whiff_rate",
            "CSW%",
            "xwOBA",
            "wOBA",
            "BA",
            "SLG",
            "HardHit%",
            "Barrel%"
        ]
    ].copy()

    performance = performance.sort_values(
        ["count", "pitch_name"]
    )

    print(performance.to_string(index=False))


# Most-used pitch in each count
for hand in ["RHB", "LHB"]:

    print("\n")
    print("=" * 65)
    print("PRIMARY PITCH VS", hand)
    print("=" * 65)

    primary_pitch = (
        pitch_counts[
            pitch_counts["batter_hand"] == hand
        ]
        .sort_values(
            ["count", "usage"],
            ascending=[True, False]
        )
        .groupby("count")
        .first()
        .reset_index()
    )

    primary_pitch = primary_pitch[
        [
            "count",
            "pitch_name",
            "usage",
            "average_velocity"
        ]
    ]

    print(primary_pitch.to_string(index=False))


# Pitch sequencing: what comes after each pitch?
sequencing_data = pitcher_data[
    pitcher_data["previous_pitch"].notna()
    & pitcher_data["batter_hand"].notna()
].copy()

sequence_counts = (
    sequencing_data
    .groupby(
        ["batter_hand", "previous_pitch", "pitch_name"]
    )
    .size()
    .reset_index(name="times_thrown")
)

sequence_totals = (
    sequence_counts
    .groupby(["batter_hand", "previous_pitch"])["times_thrown"]
    .sum()
    .reset_index(name="total_next_pitches")
)

sequence_counts = sequence_counts.merge(
    sequence_totals,
    on=["batter_hand", "previous_pitch"]
)

sequence_counts["usage"] = (
    sequence_counts["times_thrown"]
    / sequence_counts["total_next_pitches"]
    * 100
).round(1)

sequence_counts = sequence_counts.sort_values(
    ["batter_hand", "previous_pitch", "usage"],
    ascending=[True, True, False]
)


# Display pitch sequencing
for hand in ["RHB", "LHB"]:

    print("\n")
    print("=" * 65)
    print("PITCH SEQUENCING VS", hand)
    print("=" * 65)

    sequence_display = sequence_counts[
        sequence_counts["batter_hand"] == hand
    ][
        [
            "previous_pitch",
            "pitch_name",
            "times_thrown",
            "usage"
        ]
    ].copy()

    print(sequence_display.to_string(index=False))


# Most common follow-up pitch after each pitch
for hand in ["RHB", "LHB"]:

    print("\n")
    print("=" * 65)
    print("PRIMARY FOLLOW-UP PITCH VS", hand)
    print("=" * 65)

    primary_followup = (
        sequence_counts[
            sequence_counts["batter_hand"] == hand
        ]
        .sort_values(
            ["previous_pitch", "usage"],
            ascending=[True, False]
        )
        .groupby("previous_pitch")
        .first()
        .reset_index()
    )

    primary_followup = primary_followup[
        [
            "previous_pitch",
            "pitch_name",
            "times_thrown",
            "usage"
        ]
    ]

    print(primary_followup.to_string(index=False))