"""Local sample metrics used when API keys are not configured."""

# ruff: noqa: E501

from __future__ import annotations

from services.models import VideoMetric


def load_sample_videos() -> list[VideoMetric]:
    """Return deterministic sample data that mirrors the project scope."""
    rows = [
        ("netflu-01", "Netflu", "@Netflu", "Comment les createurs gagnent vraiment sur YouTube", "2026-05-08T12:00:00Z", 18420, 742, 68, 748),
        ("netflu-02", "Netflu", "@Netflu", "Les tendances streaming qui explosent en 2026", "2026-05-04T12:00:00Z", 15210, 511, 43, 681),
        ("netflu-03", "Netflu", "@Netflu", "Interview: batir une audience fidele", "2026-04-29T12:00:00Z", 8350, 214, 21, 1190),
        ("netflu-04", "Netflu", "@Netflu", "Shorts vs videos longues: que choisir?", "2026-04-25T12:00:00Z", 22280, 933, 91, 602),
        ("netflu-05", "Netflu", "@Netflu", "Le format qui booste la retention", "2026-04-20T12:00:00Z", 12840, 402, 37, 712),
        ("netflu-06", "Netflu", "@Netflu", "Analyse de chaine: erreurs frequentes", "2026-04-15T12:00:00Z", 9410, 251, 17, 834),
        ("netflu-07", "Netflu", "@Netflu", "Construire un calendrier editorial efficace", "2026-04-10T12:00:00Z", 11330, 348, 28, 905),
        ("netflu-08", "Netflu", "@Netflu", "Les miniatures qui convertissent le mieux", "2026-04-05T12:00:00Z", 19770, 801, 74, 640),
        ("netflu-09", "Netflu", "@Netflu", "Monetisation: erreurs a eviter", "2026-03-30T12:00:00Z", 10120, 299, 25, 766),
        ("netflu-10", "Netflu", "@Netflu", "Reagir aux baisses de vues sans paniquer", "2026-03-25T12:00:00Z", 6730, 156, 12, 692),
        ("playoffs-01", "ThePlayoffsTV", "@ThePlayoffsTV", "Debrief NBA: les favoris sous pression", "2026-05-09T18:30:00Z", 31240, 1220, 184, 820),
        ("playoffs-02", "ThePlayoffsTV", "@ThePlayoffsTV", "Top actions de la semaine", "2026-05-06T18:30:00Z", 42890, 1911, 236, 540),
        ("playoffs-03", "ThePlayoffsTV", "@ThePlayoffsTV", "Preview finale conference", "2026-05-02T18:30:00Z", 28430, 1044, 151, 970),
        ("playoffs-04", "ThePlayoffsTV", "@ThePlayoffsTV", "Pourquoi cette defense change tout", "2026-04-28T18:30:00Z", 19680, 621, 89, 1120),
        ("playoffs-05", "ThePlayoffsTV", "@ThePlayoffsTV", "Le rookie qui surprend la ligue", "2026-04-24T18:30:00Z", 35910, 1450, 198, 760),
        ("playoffs-06", "ThePlayoffsTV", "@ThePlayoffsTV", "Reaction a chaud apres le Game 7", "2026-04-20T18:30:00Z", 46870, 2144, 312, 690),
        ("playoffs-07", "ThePlayoffsTV", "@ThePlayoffsTV", "Analyse tactique: spacing et rythme", "2026-04-16T18:30:00Z", 17420, 512, 74, 1010),
        ("playoffs-08", "ThePlayoffsTV", "@ThePlayoffsTV", "Power ranking playoff edition", "2026-04-11T18:30:00Z", 25180, 830, 133, 880),
        ("playoffs-09", "ThePlayoffsTV", "@ThePlayoffsTV", "Les matchups a surveiller", "2026-04-07T18:30:00Z", 22650, 699, 117, 930),
        ("playoffs-10", "ThePlayoffsTV", "@ThePlayoffsTV", "Bilan de saison: surprises et flops", "2026-04-03T18:30:00Z", 14390, 388, 52, 1240),
    ]

    return [
        VideoMetric(
            video_id=video_id,
            channel_name=channel,
            channel_handle=handle,
            title=title,
            published_at=published_at,
            url=f"https://www.youtube.com/watch?v={video_id}",
            views=views,
            likes=likes,
            comments=comments,
            duration_seconds=duration,
        )
        for video_id, channel, handle, title, published_at, views, likes, comments, duration in rows
    ]
