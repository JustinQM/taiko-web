# Step 4 tasks

One file per unit of work, in dependency order. Each says what it
changes, and how it will be shown to work.

The backgrounds come first because they are the biggest asset job and
everything downstream — especially the performance pass — has to account
for what they add. The performance pass is last because it needs the
finished game to measure.

| # | Task | Repo |
|---|------|------|
| 01 | A repeatable frame-time harness | fork |
| 02 | Composite the background art into strips | private |
| 03 | The background as a canvas layer | fork |
| 04 | Dancers, on the beat | fork |
| 05 | Fever, footer, renda, chibi | fork |
| 06 | Remove the DOM and CSS background | fork |
| 07 | Crowns from the skin | both |
| 08 | The websocket reconnects | fork |
| 09 | Close the socket on unload | fork |
| 10 | The netplay branch that swallows actions | fork |
| 11 | Performance: measure, then fix | fork |

01 comes first even though it is not a feature: the backgrounds are the
largest thing ever added to the draw loop, and without a measurement
taken before them there is nothing to compare against afterwards.
