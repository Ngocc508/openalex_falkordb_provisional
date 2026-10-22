OPENALEX / FALKORDB PROVISIONAL DATASET RELEASE
================================================

Release ID:
provisional_excluded88_v1_20261021T111533206730Z

Status:
PROVISIONAL RELEASE CANDIDATE — NOT FINAL DATASET SIGNOFF

Main dataset:
data/cohort_works_2018_2025_provisional_filtered.jsonl

Verified counts:
- Works: 55119
- Retained authorship occurrences: 1118807
- Excluded unresolved occurrences: 88
- Distinct works containing exclusions: 76

Important provenance files:
- provenance/retained_authorship_source_index_map_v1.csv
- provenance/excluded_occurrence_audit_v1.csv
- provenance/exclude_unresolved_authorships_v1.csv

The index map connects filtered authorship indices back to source indices.
Use it when provenance to the original raw corpus is required.

This release intentionally does NOT include the original raw corpus.
The original raw corpus remains preserved separately in Google Drive.

This package does NOT contain verified final train/validation/test labels
or a final research signoff. Recompute graph edges and dependent labels
from the filtered dataset. Validate temporal leakage before reporting
final model metrics.

Unresolved identity occurrences were excluded only from this provisional
graph input. They were not declared to be incorrect authorships or
permanently deleted from the canonical dataset.
