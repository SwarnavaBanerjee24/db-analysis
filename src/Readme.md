# Deutsche Bahn's punctuality analysis: Does delay compound along a route?

A stop-level analysis of about 130M records from the `piebro/deutsche-bahn-data`
dataset (Nov 2025 to Jul 2026). The question I set out to answer: as a train works
its way along a route, does it steadily pile up delay, and does that play out
differently depending on the type of service?

## What I found

Delay doesn't build up evenly. The median per-stop change in delay is 0 for every
service class, so the typical stop neither gains nor loses time. There is net
compounding, but it comes from a heavy tail, and it's really a long-distance problem.

Take ICE, IC and EC. A stop adds somewhere around 0.8 to 1.4 minutes on average,
which comes out to roughly 10 minutes over a full ICE route. On its own that average
is misleading. For ICE, 42% of stops lose time and 37% claw it back; the real damage
sits in the worst 1% of stops, which pile on 38 minutes or more (49 for EC, 26 for
IC). A handful of bad stops carry almost the entire effect.

Regional services are a different story. RE, RB and S-Bahn trains mostly hold
whatever delay they started with. On the S-Bahn, 60% of stops don't move the delay
at all, and even the worst 1% add only about 3 minutes.

One caveat that cuts in the same direction: the long-distance trains are also the
ones most likely to be cancelled partway through a route (4.2% of ICE journeys), and
a cancelled train stops producing data before its worst stops ever get recorded. So
treat these figures as a floor.

## The bug that changed the answer

`train_line_ride_id` is not unique per journey. It gets reused across dates, roughly
44 times each (253k distinct IDs against 11.1M id-date pairs). Partition a per-stop
window function on that ID alone and you end up stitching about 44 unrelated days
into one sequence, at which point the real signal averages away to almost nothing.

Before I caught that, the analysis told me delay doesn't compound at all. It was
wrong, an artifact of the broken grain. The fix was to key every per-journey
calculation on `(train_line_ride_id, date)`. One limitation I left in: a journey that
runs past midnight gets split in two by the date boundary. It only touches a small
number of late-night services, so I let it stand.

You'll need Python with duckdb, pandas and matplotlib.