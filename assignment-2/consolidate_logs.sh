#!/bin/bash

rm -f combine.tmp

cat logs_node_0/dump.txt > combine.tmp
cat logs_node_1/dump.txt >> combine.tmp
cat logs_node_2/dump.txt >> combine.tmp

sort combine.tmp > log.tmp

rm combine.tmp
