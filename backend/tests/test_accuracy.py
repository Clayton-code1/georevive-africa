from georevive.rescue.accuracy import _prf, key_of


def test_label_keys_normalise():
    assert key_of("assay", "12 dwt. per ton") == ("assay", "12 dwt")
    assert key_of("assay", "3.5 g/t") == ("assay", "3.5 g/t")
    assert key_of("mine", "Jumbo Mine") == ("mine", "jumbo")
    assert key_of("location_desc", "15 miles north-east of Salisbury") == ("location_desc", "15 salisbury")
    assert key_of("rock_unit", "Bulawayan Group") == ("rock_unit", "bulawayan group")


def test_precision_recall():
    p, r, f = _prf(8, 2, 4)
    assert p == 0.8 and abs(r - 8 / 12) < 1e-9 and 0 < f < 1
    assert _prf(0, 0, 0) == (None, None, None)
