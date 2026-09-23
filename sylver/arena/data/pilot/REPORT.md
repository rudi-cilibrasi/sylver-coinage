# Proof-search arena pilot

This is an offline implementation pilot with a scripted model test double.
It measures local strategies and protocol overhead; it is not evidence that
real language-model prompt evolution improves mathematical search.

The training panel, held-out checkpoint, seed, repeats, CPU/model limits,
and nine-candidate cap were declared before evaluation. All deployments
use identical per-task profiles. Generation overhead is separate from each
candidate's episode score. No hidden outcomes or proofs enter selection.

Evolution spent 3.505604 CPU seconds including candidate evaluations; proposal generation accounted for 0.110136 seconds. Remote requests, tokens, and spending: zero. Local mock-provider usage is in episode receipts.

## Candidate history

| Candidate | Mode | Status | Mean log(S), training | Parent |
| --- | --- | --- | ---: | --- |
| 6004e2609ebf | policy | valid | 5.9568091578088325 | seed |
| c52917091f29 | policy | valid | 5.531868900255987 | seed |
| cf6c7b1a480a | policy | valid | 5.531920275069811 | seed |
| 301cb9f7ccbe | prompt | valid | 5.533997085856105 | seed |
| e39d3f5019e5 | prompt | valid | 5.5379829570137264 | seed |
| 39af35860595 | prompt | valid | 5.515805962986795 | c52917091f29 |
| 13e431242e45 | prompt | invalid | None | c52917091f29 |
| 6b79cd6e57b1 | policy | valid | 5.614599136887414 | 39af35860595 |
| 98decff1721b | policy | invalid | None | 39af35860595 |

# Training repetitions

Scores are compared only within an identical target, snapshot, verifier, and execution profile.

C is canonical UTF-8 proof bytes; T is discovery + verification CPU seconds. Lower S=(C+100)*(T+1) is better.

## Target {4,5} — 3e103a918748c46f

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| routes-short | valid | N | 73 | 0.041529 | 0.039988 | 0.081517 | 187.102422 | 5.231656 |
| interleaved | valid | N | 73 | 0.042609 | 0.039630 | 0.082240 | 187.227443 | 5.232324 |
| interleaved | valid | N | 73 | 0.042188 | 0.040849 | 0.083037 | 187.365472 | 5.233061 |
| routes-short | valid | N | 73 | 0.042109 | 0.041046 | 0.083155 | 187.385803 | 5.233170 |
| interleaved | valid | N | 73 | 0.042219 | 0.041412 | 0.083630 | 187.468075 | 5.233609 |
| routes-short | valid | N | 73 | 0.042750 | 0.046544 | 0.089295 | 188.447953 | 5.238822 |
| evolved-prompt | valid | N | 73 | 0.114866 | 0.040787 | 0.155653 | 199.927902 | 5.297957 |
| evolved-prompt | valid | N | 73 | 0.121248 | 0.040129 | 0.161377 | 200.918286 | 5.302898 |
| evolved-prompt | valid | N | 73 | 0.129218 | 0.040272 | 0.169490 | 202.321704 | 5.309859 |
| mock-prompt-seed | valid | N | 73 | 0.137086 | 0.040551 | 0.177636 | 203.731097 | 5.316801 |
| mock-prompt-seed | valid | N | 73 | 0.137831 | 0.040734 | 0.178565 | 203.891754 | 5.317589 |
| mock-prompt-seed | valid | N | 73 | 0.139370 | 0.041766 | 0.181136 | 204.336523 | 5.319768 |
| evolved-policy | valid | N | 139 | 0.042296 | 0.037556 | 0.079852 | 258.084581 | 5.553287 |
| evolved-policy | valid | N | 139 | 0.043237 | 0.040425 | 0.083662 | 258.995130 | 5.556809 |
| increasing | valid | N | 139 | 0.045369 | 0.039580 | 0.084949 | 259.302859 | 5.557997 |
| evolved-policy | valid | N | 139 | 0.044253 | 0.041416 | 0.085669 | 259.474880 | 5.558660 |
| increasing | valid | N | 139 | 0.045715 | 0.040423 | 0.086138 | 259.586917 | 5.559092 |
| increasing | valid | N | 139 | 0.052566 | 0.041033 | 0.093599 | 261.370281 | 5.565938 |

evolved-policy: 3/3 valid; S min/median/max = 258.084581/258.995130/259.474880; stdev = 0.706186.
evolved-prompt: 3/3 valid; S min/median/max = 199.927902/200.918286/202.321704; stdev = 1.202826.
increasing: 3/3 valid; S min/median/max = 259.302859/259.586917/261.370281; stdev = 1.120662.
interleaved: 3/3 valid; S min/median/max = 187.227443/187.365472/187.468075; stdev = 0.120750.
mock-prompt-seed: 3/3 valid; S min/median/max = 203.731097/203.891754/204.336523; stdev = 0.313627.
routes-short: 3/3 valid; S min/median/max = 187.102422/187.385803/188.447953; stdev = 0.709333.

## Target {4,5,11} — c1926648b1444aae

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| interleaved | valid | P | 79 | 0.040946 | 0.038184 | 0.079129 | 193.164098 | 5.263540 |
| routes-short | valid | P | 79 | 0.042776 | 0.039354 | 0.082130 | 193.701295 | 5.266317 |
| interleaved | valid | P | 79 | 0.041363 | 0.040815 | 0.082178 | 193.709812 | 5.266361 |
| evolved-policy | valid | P | 79 | 0.042209 | 0.040359 | 0.082569 | 193.779827 | 5.266723 |
| routes-short | valid | P | 79 | 0.042542 | 0.040927 | 0.083470 | 193.941092 | 5.267554 |
| routes-short | valid | P | 79 | 0.042991 | 0.040535 | 0.083526 | 193.951091 | 5.267606 |
| evolved-policy | valid | P | 79 | 0.043260 | 0.040862 | 0.084122 | 194.057878 | 5.268156 |
| evolved-policy | valid | P | 79 | 0.042540 | 0.041788 | 0.084329 | 194.094815 | 5.268347 |
| interleaved | valid | P | 79 | 0.043093 | 0.041610 | 0.084704 | 194.161980 | 5.268693 |
| evolved-prompt | valid | P | 79 | 0.123021 | 0.039884 | 0.162905 | 208.160040 | 5.338307 |
| evolved-prompt | valid | P | 79 | 0.130513 | 0.039576 | 0.170089 | 209.445983 | 5.344466 |
| evolved-prompt | valid | P | 79 | 0.128669 | 0.041773 | 0.170441 | 209.508969 | 5.344767 |
| mock-prompt-seed | valid | P | 79 | 0.134418 | 0.041331 | 0.175749 | 210.459033 | 5.349291 |
| mock-prompt-seed | valid | P | 79 | 0.141565 | 0.039896 | 0.181461 | 211.481576 | 5.354138 |
| mock-prompt-seed | valid | P | 79 | 0.145152 | 0.041123 | 0.186275 | 212.343208 | 5.358204 |
| increasing | valid | P | 594 | 0.042249 | 0.040142 | 0.082391 | 751.179382 | 6.621644 |
| increasing | valid | P | 594 | 0.042537 | 0.042335 | 0.084872 | 752.901118 | 6.623934 |
| increasing | valid | P | 594 | 0.043477 | 0.041682 | 0.085159 | 753.100631 | 6.624199 |

evolved-policy: 3/3 valid; S min/median/max = 193.779827/194.057878/194.094815; stdev = 0.172189.
evolved-prompt: 3/3 valid; S min/median/max = 208.160040/209.445983/209.508969; stdev = 0.761274.
increasing: 3/3 valid; S min/median/max = 751.179382/752.901118/753.100631; stdev = 1.056360.
interleaved: 3/3 valid; S min/median/max = 193.164098/193.709812/194.161980; stdev = 0.499671.
mock-prompt-seed: 3/3 valid; S min/median/max = 210.459033/211.481576/212.343208; stdev = 0.943232.
routes-short: 3/3 valid; S min/median/max = 193.701295/193.941092/193.951091; stdev = 0.141422.

## Target {4,6} — d0c19552109dd807

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| interleaved | valid | P | 301 | 0.037021 | 0.036707 | 0.073728 | 430.564883 | 6.065098 |
| evolved-policy | valid | P | 301 | 0.037082 | 0.037064 | 0.074146 | 430.732425 | 6.065487 |
| evolved-policy | valid | P | 301 | 0.039132 | 0.035980 | 0.075112 | 431.119833 | 6.066386 |
| interleaved | valid | P | 301 | 0.037825 | 0.037338 | 0.075163 | 431.140532 | 6.066434 |
| evolved-policy | valid | P | 301 | 0.037975 | 0.037592 | 0.075567 | 431.302252 | 6.066809 |
| routes-short | valid | P | 301 | 0.038614 | 0.036973 | 0.075587 | 431.310402 | 6.066828 |
| routes-short | valid | P | 301 | 0.037560 | 0.038190 | 0.075750 | 431.375845 | 6.066980 |
| increasing | valid | P | 301 | 0.038582 | 0.037352 | 0.075934 | 431.449405 | 6.067150 |
| increasing | valid | P | 301 | 0.037348 | 0.038608 | 0.075956 | 431.458394 | 6.067171 |
| increasing | valid | P | 301 | 0.039055 | 0.037239 | 0.076294 | 431.593782 | 6.067485 |
| interleaved | valid | P | 301 | 0.039044 | 0.037394 | 0.076438 | 431.651753 | 6.067619 |
| routes-short | valid | P | 301 | 0.038134 | 0.038584 | 0.076718 | 431.763924 | 6.067879 |
| evolved-prompt | valid | P | 301 | 0.091125 | 0.037009 | 0.128134 | 452.381721 | 6.114526 |
| evolved-prompt | valid | P | 301 | 0.090989 | 0.037882 | 0.128872 | 452.677551 | 6.115180 |
| evolved-prompt | valid | P | 301 | 0.092279 | 0.038117 | 0.130396 | 453.288840 | 6.116530 |
| mock-prompt-seed | valid | P | 301 | 0.102132 | 0.038045 | 0.140177 | 457.210782 | 6.125145 |
| mock-prompt-seed | valid | P | 301 | 0.102435 | 0.038022 | 0.140457 | 457.323279 | 6.125391 |
| mock-prompt-seed | valid | P | 301 | 0.108251 | 0.037611 | 0.145861 | 459.490402 | 6.130118 |

evolved-policy: 3/3 valid; S min/median/max = 430.732425/431.119833/431.302252; stdev = 0.290993.
evolved-prompt: 3/3 valid; S min/median/max = 452.381721/452.677551/453.288840; stdev = 0.462611.
increasing: 3/3 valid; S min/median/max = 431.449405/431.458394/431.593782; stdev = 0.080886.
interleaved: 3/3 valid; S min/median/max = 430.564883/431.140532/431.651753; stdev = 0.543754.
mock-prompt-seed: 3/3 valid; S min/median/max = 457.210782/457.323279/459.490402; stdev = 1.284896.
routes-short: 3/3 valid; S min/median/max = 431.310402/431.375845/431.763924; stdev = 0.245143.

## Target {6,7} — e7f907ece0b85082

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| evolved-prompt | valid | N | 73 | 0.116832 | 0.040029 | 0.156861 | 200.136906 | 5.299002 |
| evolved-prompt | valid | N | 73 | 0.117837 | 0.040294 | 0.158131 | 200.356636 | 5.300099 |
| evolved-prompt | valid | N | 73 | 0.125471 | 0.039906 | 0.165377 | 201.610220 | 5.306336 |
| mock-prompt-seed | valid | N | 73 | 0.136674 | 0.039589 | 0.176263 | 203.493508 | 5.315634 |
| mock-prompt-seed | valid | N | 73 | 0.143569 | 0.041715 | 0.185284 | 205.054069 | 5.323274 |
| mock-prompt-seed | valid | N | 73 | 0.147573 | 0.039538 | 0.187111 | 205.370188 | 5.324814 |
| routes-short | valid | N | 139 | 0.043565 | 0.040043 | 0.083607 | 258.982115 | 5.556759 |
| interleaved | valid | N | 139 | 0.042890 | 0.040778 | 0.083668 | 258.996567 | 5.556815 |
| interleaved | valid | N | 139 | 0.043682 | 0.040081 | 0.083763 | 259.019317 | 5.556903 |
| routes-short | valid | N | 139 | 0.043526 | 0.040302 | 0.083828 | 259.034816 | 5.556962 |
| routes-short | valid | N | 139 | 0.042443 | 0.041528 | 0.083971 | 259.069105 | 5.557095 |
| interleaved | valid | N | 139 | 0.044065 | 0.040016 | 0.084081 | 259.095256 | 5.557196 |
| evolved-policy | valid | N | 139 | 0.047181 | 0.040828 | 0.088009 | 260.034121 | 5.560813 |
| evolved-policy | valid | N | 139 | 0.048733 | 0.039833 | 0.088566 | 260.167272 | 5.561325 |
| evolved-policy | valid | N | 139 | 0.047615 | 0.041307 | 0.088922 | 260.252338 | 5.561652 |
| increasing | valid | N | 139 | 0.062473 | 0.039895 | 0.102367 | 263.465810 | 5.573924 |
| increasing | valid | N | 139 | 0.061623 | 0.041900 | 0.103523 | 263.741898 | 5.574971 |
| increasing | valid | N | 139 | 0.063587 | 0.040731 | 0.104318 | 263.931996 | 5.575691 |

evolved-policy: 3/3 valid; S min/median/max = 260.034121/260.167272/260.252338; stdev = 0.109988.
evolved-prompt: 3/3 valid; S min/median/max = 200.136906/200.356636/201.610220; stdev = 0.794817.
increasing: 3/3 valid; S min/median/max = 263.465810/263.741898/263.931996; stdev = 0.234411.
interleaved: 3/3 valid; S min/median/max = 258.996567/259.019317/259.095256; stdev = 0.051678.
mock-prompt-seed: 3/3 valid; S min/median/max = 203.493508/205.054069/205.370188; stdev = 1.004756.
routes-short: 3/3 valid; S min/median/max = 258.982115/259.034816/259.069105; stdev = 0.043819.

## Coverage (separate from per-target scores)

- evolved-policy: 4/4 distinct tasks solved.
- evolved-prompt: 4/4 distinct tasks solved.
- increasing: 4/4 distinct tasks solved.
- interleaved: 4/4 distinct tasks solved.
- mock-prompt-seed: 4/4 distinct tasks solved.
- routes-short: 4/4 distinct tasks solved.

# Held-out repetitions

Scores are compared only within an identical target, snapshot, verifier, and execution profile.

C is canonical UTF-8 proof bytes; T is discovery + verification CPU seconds. Lower S=(C+100)*(T+1) is better.

## Target {6,7,11} — 12a0d60ee1ae5987

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| routes-short | valid | N | 79 | 0.043705 | 0.038250 | 0.081955 | 193.669953 | 5.266155 |
| interleaved | valid | N | 79 | 0.041777 | 0.040359 | 0.082136 | 193.702367 | 5.266323 |
| interleaved | valid | N | 79 | 0.042853 | 0.040091 | 0.082943 | 193.846879 | 5.267069 |
| routes-short | valid | N | 79 | 0.041989 | 0.041040 | 0.083029 | 193.862236 | 5.267148 |
| interleaved | valid | N | 79 | 0.042636 | 0.040598 | 0.083234 | 193.898884 | 5.267337 |
| routes-short | valid | N | 79 | 0.044380 | 0.040488 | 0.084868 | 194.191428 | 5.268844 |
| evolved-prompt | valid | N | 79 | 0.119024 | 0.039623 | 0.158647 | 207.397742 | 5.334638 |
| evolved-prompt | valid | N | 79 | 0.121798 | 0.040581 | 0.162378 | 208.065743 | 5.337854 |
| evolved-prompt | valid | N | 79 | 0.127936 | 0.040429 | 0.168365 | 209.137350 | 5.342991 |
| mock-prompt-seed | valid | N | 79 | 0.133203 | 0.040018 | 0.173221 | 210.006506 | 5.347139 |
| mock-prompt-seed | valid | N | 79 | 0.138642 | 0.040762 | 0.179404 | 211.113268 | 5.352395 |
| mock-prompt-seed | valid | N | 79 | 0.143070 | 0.041988 | 0.185058 | 212.125325 | 5.357177 |
| evolved-policy | valid | N | 148 | 0.043142 | 0.039726 | 0.082867 | 268.551132 | 5.593041 |
| evolved-policy | valid | N | 148 | 0.042871 | 0.040973 | 0.083844 | 268.793252 | 5.593943 |
| increasing | valid | N | 148 | 0.046091 | 0.041088 | 0.087179 | 269.620355 | 5.597015 |
| increasing | valid | N | 148 | 0.046676 | 0.040971 | 0.087647 | 269.736501 | 5.597446 |
| evolved-policy | valid | N | 148 | 0.047452 | 0.040902 | 0.088355 | 269.911971 | 5.598096 |
| increasing | valid | N | 148 | 0.047542 | 0.041943 | 0.089486 | 270.192465 | 5.599135 |

evolved-policy: 3/3 valid; S min/median/max = 268.551132/268.793252/269.911971; stdev = 0.725952.
evolved-prompt: 3/3 valid; S min/median/max = 207.397742/208.065743/209.137350; stdev = 0.877573.
increasing: 3/3 valid; S min/median/max = 269.620355/269.736501/270.192465; stdev = 0.302408.
interleaved: 3/3 valid; S min/median/max = 193.702367/193.846879/193.898884; stdev = 0.101823.
mock-prompt-seed: 3/3 valid; S min/median/max = 210.006506/211.113268/212.125325; stdev = 1.059762.
routes-short: 3/3 valid; S min/median/max = 193.669953/193.862236/194.191428; stdev = 0.263716.

## Target {5,7} — 1a0671a9d83ccda6

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| evolved-prompt | valid | N | 73 | 0.114775 | 0.041976 | 0.156751 | 200.117947 | 5.298907 |
| evolved-prompt | valid | N | 73 | 0.123815 | 0.040277 | 0.164092 | 201.387831 | 5.305233 |
| evolved-prompt | valid | N | 73 | 0.124444 | 0.041175 | 0.165619 | 201.652142 | 5.306544 |
| mock-prompt-seed | valid | N | 73 | 0.140162 | 0.039830 | 0.179992 | 204.138530 | 5.318799 |
| mock-prompt-seed | valid | N | 73 | 0.140511 | 0.040111 | 0.180622 | 204.247536 | 5.319333 |
| mock-prompt-seed | valid | N | 73 | 0.140983 | 0.039684 | 0.180667 | 204.255420 | 5.319371 |
| evolved-policy | valid | N | 136 | 0.042443 | 0.040118 | 0.082561 | 255.484480 | 5.543162 |
| evolved-policy | valid | N | 136 | 0.042300 | 0.041082 | 0.083382 | 255.678175 | 5.543920 |
| routes-short | valid | N | 136 | 0.043452 | 0.040093 | 0.083545 | 255.716729 | 5.544070 |
| interleaved | valid | N | 136 | 0.043341 | 0.040941 | 0.084282 | 255.890500 | 5.544750 |
| routes-short | valid | N | 136 | 0.044780 | 0.039519 | 0.084299 | 255.894607 | 5.544766 |
| routes-short | valid | N | 136 | 0.043491 | 0.041049 | 0.084540 | 255.951516 | 5.544988 |
| interleaved | valid | N | 136 | 0.044433 | 0.040281 | 0.084714 | 255.992533 | 5.545148 |
| evolved-policy | valid | N | 136 | 0.044011 | 0.040979 | 0.084990 | 256.057728 | 5.545403 |
| interleaved | valid | N | 136 | 0.043711 | 0.042384 | 0.086096 | 256.318554 | 5.546421 |
| increasing | valid | N | 136 | 0.046288 | 0.041002 | 0.087290 | 256.600465 | 5.547520 |
| increasing | valid | N | 136 | 0.048089 | 0.039963 | 0.088051 | 256.780151 | 5.548220 |
| increasing | valid | N | 136 | 0.050332 | 0.038458 | 0.088790 | 256.954492 | 5.548899 |

evolved-policy: 3/3 valid; S min/median/max = 255.484480/255.678175/256.057728; stdev = 0.291603.
evolved-prompt: 3/3 valid; S min/median/max = 200.117947/201.387831/201.652142; stdev = 0.820185.
increasing: 3/3 valid; S min/median/max = 256.600465/256.780151/256.954492; stdev = 0.177020.
interleaved: 3/3 valid; S min/median/max = 255.890500/255.992533/256.318554; stdev = 0.223581.
mock-prompt-seed: 3/3 valid; S min/median/max = 204.138530/204.247536/204.255420; stdev = 0.065330.
routes-short: 3/3 valid; S min/median/max = 255.716729/255.894607/255.951516; stdev = 0.122477.

## Target {4,6,9} — 20d893dff68971b9

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| interleaved | valid | N | 77 | 0.041365 | 0.039865 | 0.081230 | 191.377723 | 5.254249 |
| routes-short | valid | N | 77 | 0.042533 | 0.039879 | 0.082412 | 191.587012 | 5.255342 |
| interleaved | valid | N | 77 | 0.042261 | 0.040385 | 0.082646 | 191.628387 | 5.255558 |
| routes-short | valid | N | 77 | 0.043172 | 0.040197 | 0.083369 | 191.756308 | 5.256225 |
| routes-short | valid | N | 77 | 0.043769 | 0.039602 | 0.083371 | 191.756660 | 5.256227 |
| interleaved | valid | N | 77 | 0.043318 | 0.041414 | 0.084732 | 191.997567 | 5.257483 |
| evolved-prompt | valid | N | 77 | 0.125096 | 0.039508 | 0.164604 | 206.134845 | 5.328531 |
| evolved-prompt | valid | N | 77 | 0.125471 | 0.039624 | 0.165094 | 206.221707 | 5.328952 |
| evolved-prompt | valid | N | 77 | 0.124692 | 0.041793 | 0.166485 | 206.467800 | 5.330144 |
| mock-prompt-seed | valid | N | 77 | 0.137674 | 0.041030 | 0.178704 | 208.630585 | 5.340565 |
| mock-prompt-seed | valid | N | 77 | 0.139956 | 0.040337 | 0.180293 | 208.911847 | 5.341912 |
| mock-prompt-seed | valid | N | 77 | 0.142976 | 0.040757 | 0.183733 | 209.520709 | 5.344823 |
| evolved-policy | valid | N | 147 | 0.041638 | 0.040101 | 0.081739 | 267.189567 | 5.587958 |
| evolved-policy | valid | N | 147 | 0.042716 | 0.040124 | 0.082840 | 267.461407 | 5.588975 |
| evolved-policy | valid | N | 147 | 0.041320 | 0.041746 | 0.083066 | 267.517318 | 5.589184 |
| increasing | valid | N | 147 | 0.044704 | 0.039454 | 0.084158 | 267.787091 | 5.590192 |
| increasing | valid | N | 147 | 0.044890 | 0.039426 | 0.084316 | 267.826073 | 5.590338 |
| increasing | valid | N | 147 | 0.046806 | 0.040450 | 0.087255 | 268.552095 | 5.593045 |

evolved-policy: 3/3 valid; S min/median/max = 267.189567/267.461407/267.517318; stdev = 0.175330.
evolved-prompt: 3/3 valid; S min/median/max = 206.134845/206.221707/206.467800; stdev = 0.172707.
increasing: 3/3 valid; S min/median/max = 267.787091/267.826073/268.552095; stdev = 0.430864.
interleaved: 3/3 valid; S min/median/max = 191.377723/191.628387/191.997567; stdev = 0.311804.
mock-prompt-seed: 3/3 valid; S min/median/max = 208.630585/208.911847/209.520709; stdev = 0.454999.
routes-short: 3/3 valid; S min/median/max = 191.587012/191.756308/191.756660; stdev = 0.097845.

## Target {8,9} — 86023d729765c14f

| Competitor | Status | Outcome | C | Discovery CPU | Verification CPU | T | S | log_score |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| evolved-prompt | valid | N | 73 | 0.118054 | 0.040953 | 0.159007 | 200.508239 | 5.300855 |
| evolved-prompt | valid | N | 73 | 0.126781 | 0.040210 | 0.166991 | 201.889509 | 5.307721 |
| evolved-prompt | valid | N | 73 | 0.130798 | 0.041111 | 0.171909 | 202.740258 | 5.311926 |
| mock-prompt-seed | valid | N | 73 | 0.138237 | 0.040739 | 0.178977 | 203.962948 | 5.317938 |
| mock-prompt-seed | valid | N | 73 | 0.144021 | 0.039573 | 0.183594 | 204.761839 | 5.321848 |
| mock-prompt-seed | valid | N | 73 | 0.145432 | 0.040419 | 0.185851 | 205.152194 | 5.323752 |
| interleaved | valid | N | 139 | 0.052775 | 0.040221 | 0.092997 | 261.226176 | 5.565387 |
| routes-short | valid | N | 139 | 0.053189 | 0.040072 | 0.093261 | 261.289465 | 5.565629 |
| routes-short | valid | N | 139 | 0.053066 | 0.040276 | 0.093342 | 261.308673 | 5.565702 |
| interleaved | valid | N | 139 | 0.052316 | 0.041062 | 0.093379 | 261.317519 | 5.565736 |
| routes-short | valid | N | 139 | 0.054101 | 0.039373 | 0.093474 | 261.340342 | 5.565824 |
| interleaved | valid | N | 139 | 0.053826 | 0.039689 | 0.093514 | 261.349962 | 5.565860 |
| evolved-policy | valid | N | 139 | 0.058586 | 0.039489 | 0.098075 | 262.439893 | 5.570022 |
| evolved-policy | valid | N | 139 | 0.058260 | 0.039940 | 0.098201 | 262.470008 | 5.570137 |
| evolved-policy | valid | N | 139 | 0.060223 | 0.040849 | 0.101072 | 263.156241 | 5.572748 |
| increasing | valid | N | 139 | 0.084736 | 0.042434 | 0.127170 | 269.393549 | 5.596173 |
| increasing | valid | N | 139 | 0.087891 | 0.040582 | 0.128473 | 269.704972 | 5.597329 |
| increasing | valid | N | 139 | 0.090068 | 0.041414 | 0.131481 | 270.424068 | 5.599991 |

evolved-policy: 3/3 valid; S min/median/max = 262.439893/262.470008/263.156241; stdev = 0.405171.
evolved-prompt: 3/3 valid; S min/median/max = 200.508239/201.889509/202.740258; stdev = 1.126468.
increasing: 3/3 valid; S min/median/max = 269.393549/269.704972/270.424068; stdev = 0.528528.
interleaved: 3/3 valid; S min/median/max = 261.226176/261.317519/261.349962; stdev = 0.064186.
mock-prompt-seed: 3/3 valid; S min/median/max = 203.962948/204.761839/205.152194; stdev = 0.606206.
routes-short: 3/3 valid; S min/median/max = 261.289465/261.308673/261.340342; stdev = 0.025692.

## Coverage (separate from per-target scores)

- evolved-policy: 4/4 distinct tasks solved.
- evolved-prompt: 4/4 distinct tasks solved.
- increasing: 4/4 distinct tasks solved.
- interleaved: 4/4 distinct tasks solved.
- mock-prompt-seed: 4/4 distinct tasks solved.
- routes-short: 4/4 distinct tasks solved.

## Per-target held-out comparison

evolved-policy: lower median S than interleaved on 1/4 comparable held-out targets; no cross-target raw-score sum.

evolved-prompt: lower median S than mock-prompt-seed on 4/4 comparable held-out targets; no cross-target raw-score sum.


## Decision: revise before a live evolutionary campaign

The harness compares valid proofs, rejects malformed proposals, and retains
failures and timing distributions. These small, public finite/short fixtures
are an engineering control, and timing differences can be dominated by
process startup. The prompt arm uses a deterministic script, not an LLM.
Consequently this pilot does not establish a reproducible evolutionary search
advantage on difficult W branches. Keep the fixed verifier/accounting and
expand the predeclared training panel before spending on remote-model/live
search. Do not select a winner using this held-out report.

No new live discovery was attempted or admitted. W's current five unresolved
moves are 70,86,92,108,118. The original six post-PR5 challenges also include
102, now a public regression because PR13 published reply 95. Resolving W
would imply Q N; U P still also requires X N. Opening 16 remains unresolved.

Reproduce with `python -m sylver.arena pilot --output /tmp/arena-pilot`.
Use the recorded seed and repeat count for another run. Selection can be
replayed exactly from recorded measurements; wall/CPU timings and remote
model responses are not promised bitwise reproducible. Each episode includes
a bundle, policy/agent manifest, canonical certificate, protocol/model
transcripts, hashes, CPU receipts, and an independent replay command.
