# Ukrainian Stress Dictionary Shards

This repository contains a processed version of the **ukrainian-word-stress-dictionary**.

## Source

The source data was obtained from the **ukrainian-word-stress-dictionary** repository:

https://github.com/lang-uk/ukrainian-word-stress-dictionary

According to the original project description, the dictionary is based on the **"Slovnyky Ukrainy" (Dictionaries of Ukraine)** developed by the **Ukrainian Language-Information Fund of the National Academy of Sciences of Ukraine**.

The original dictionary contains approximately **2.9 million Ukrainian word forms and phrases** with stress marks.

## Purpose

This repository does not modify the linguistic data.

Its purpose is to prepare the dictionary for efficient use in the **Manuscript** writing platform by splitting it into small shards and generating data structures optimized for fast client-side loading.

The generated datasets are used in two independent modules.

### `stress/`

A sharded stress dictionary used by the Manuscript poetry editor.

### `rhymes/`

Transformed and optimized data used by the Manuscript rhyme generator.

## Processing

The processing pipeline:

* reads the original dictionary;
* splits entries into smaller shards;
* generates data structures optimized for fast loading and lookup;
* preserves the original stress information.

Only the storage format is changed. The linguistic data itself remains unchanged.

## Attribution

This repository contains derived data generated from the **ukrainian-word-stress-dictionary**, which, according to its documentation, is based on the **"Slovnyky Ukrainy"** database of the **Ukrainian Language-Information Fund of the National Academy of Sciences of Ukraine**.

Original repository:
https://github.com/lang-uk/ukrainian-word-stress-dictionary

## Note

At the time this repository was created, the original project did not include a separate license file. If the original author publishes or updates the licensing terms in the future, this repository will be updated accordingly.
