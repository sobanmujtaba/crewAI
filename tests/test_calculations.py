from src import calculations as c


def test_dti():
    assert c.dti(2100, 8200) == 25.61


def test_ltv():
    assert c.ltv(320000, 410000) == 78.05


def test_zero_division_returns_none():
    assert c.dti(100, 0) is None


def test_funds_to_close():
    assert c.funds_to_close(400000, 320000, 3) == 92000
