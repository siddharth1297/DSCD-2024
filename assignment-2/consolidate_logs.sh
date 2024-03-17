#!/bin/bash

rm -f dump.txt

cat logs_node_0/dump.txt > dump.txt
cat logs_node_1/dump.txt >> dump.txt
cat logs_node_2/dump.txt >> dump.txt

sort dump.txt
