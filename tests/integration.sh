#!/bin/bash

# exit when any command fails
set -e

species='Heteronotia binoei'
sample='tests/data/test_points/test_points.shp'
buffer=2.0
biovars=dem,bio01

crumbs-get-gbif \
      --species $species  \
      --points $sample \
      --limit 30 \
      --year "1950,2022" \
      --buffer $buffer \
      --output occurrences

presences='occurrences.shp'

crumbs-get-chelsa \
      --variables $biovars \
      --timesID 19 \
      --points $sample \
      --buffer $buffer \
      --cleanup

crumbs-fit-sdm \
      --species $species \
      --presences $presences \
      --nb-backround 30 \
      --variables $biovars \
      --buffer $buffer \
      --cleanup
