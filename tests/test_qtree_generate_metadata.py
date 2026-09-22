from collections import Counter

from qtree.generate_metadata import PER_FOLDER_TEST, PER_FOLDER_VALIDATION, load_manifest
from qtree.tree import FOLDERS, true_folder


def test_manifest_stratification():
    forms = load_manifest()
    for split, per_folder in (("test", PER_FOLDER_TEST), ("validation", PER_FOLDER_VALIDATION)):
        dist = Counter(f.true_folder for f in forms if f.split == split)
        assert dist == {f: per_folder for f in FOLDERS}


def test_manifest_true_folder_matches_recomputed_ground_truth():
    forms = load_manifest()
    for form in forms:
        assert form.true_folder == true_folder(form.answers)


def test_manifest_form_ids_unique():
    forms = load_manifest()
    ids = [f.form_id for f in forms]
    assert len(ids) == len(set(ids))


def test_manifest_total_count():
    forms = load_manifest()
    expected = len(FOLDERS) * (PER_FOLDER_TEST + PER_FOLDER_VALIDATION)
    assert len(forms) == expected
