from datetime import datetime

import pytest

from direct_indexing.custom_fields.currency_conversion import (
    convert, convert_currencies_from_dict, convert_currencies_from_list, currency_conversion, get_ym,
    save_converted_value_to_data
)
from direct_indexing.custom_fields.models import currencies


def test_currency_conversion(mocker, fixture_currencies):
    ret = (None, None, None, None)
    mock_convert_list = mocker.patch('direct_indexing.custom_fields.currency_conversion.convert_currencies_from_list', return_value=ret)  # NOQA: 501
    mock_convert_dict = mocker.patch('direct_indexing.custom_fields.currency_conversion.convert_currencies_from_dict', return_value=ret)  # NOQA: 501
    mock_save = mocker.patch('direct_indexing.custom_fields.currency_conversion.save_converted_value_to_data')

    # Test nothing changes in the data if no currencies are provided
    res = currency_conversion({}, fixture_currencies)
    mock_convert_list.assert_not_called()
    mock_convert_dict.assert_not_called()
    mock_save.assert_not_called()
    assert res == {}

    # Test the convert_currencies_from_list is called twice when data contains a budget
    data = {'budget': []}
    mock_save.return_value = data
    data = currency_conversion(data, fixture_currencies)
    assert mock_convert_list.call_count == 2
    mock_convert_dict.assert_not_called()
    assert mock_save.call_count == 2

    # Test the convert_currencies_from_dict is called twice when data contains a transaction
    mock_convert_list.reset_mock(), mock_convert_dict.reset_mock(), mock_save.reset_mock()
    data = {'transaction': {}}
    mock_save.return_value = data
    data = currency_conversion(data, fixture_currencies)
    mock_convert_list.assert_not_called()
    assert mock_convert_dict.call_count == 2
    assert mock_save.call_count == 2

    # Test the convert_currencies_from_dict is called twice when data contains a transaction, and list when data contains a budget or planned-disbursement  # NOQA: 501
    mock_convert_list.reset_mock(), mock_convert_dict.reset_mock(), mock_save.reset_mock()
    data = {'transaction': {}, 'budget': [], 'planned-disbursement': []}
    mock_save.return_value = data
    data = currency_conversion(data, fixture_currencies)
    assert mock_convert_list.call_count == 4
    assert mock_convert_dict.call_count == 2
    assert mock_save.call_count == 6

    # Test the default currency is passed to convert_from_dict when provided
    mock_convert_list.reset_mock(), mock_convert_dict.reset_mock(), mock_save.reset_mock()
    data = {'default-currency': "KRR", 'transaction': {}}
    mock_save.return_value = data
    data = currency_conversion(data, fixture_currencies)
    assert mock_convert_dict.call_count == 2
    # assert the 4th passed argument in call_args is the default currency
    assert mock_convert_dict.call_args[0][3] == "KRR"


def test_convert_currencies_from_list(mocker, fixture_currencies):
    # convert result for convert({value: 1, 'value.currency': 'EUR'}, currencies, 'USD', 'USD')
    convert_ex_res = (1.0705273292815591, 0.9341190763164442, 'EUR')  # Values based on fixture_currencies euro to gbp
    # mock convert to return convert ex res
    mock_convert = mocker.patch('direct_indexing.custom_fields.currency_conversion.convert', return_value=convert_ex_res)  # NOQA: 501
    data = {"budget": [{}]}
    field = "budget"
    currencies = fixture_currencies
    default_currency = None
    curr_convert = 'USD'

    ex_res = ([convert_ex_res[0]], [convert_ex_res[1]], convert_ex_res[2], [])
    assert convert_currencies_from_list(data, field, currencies, default_currency, [], [], "", [], curr_convert) == ex_res  # NOQA: 501
    mock_convert.assert_called_once()

    # Test that if the field is transaction, the transaction type code is added to t_type
    field = "transaction"
    data = {"transaction": [{"transaction-type": {"code": "11"}}]}
    ex_res = ([convert_ex_res[0]], [convert_ex_res[1]], convert_ex_res[2], ["11"])
    assert convert_currencies_from_list(data, field, currencies, default_currency, [], [], "", [], curr_convert) == ex_res  # NOQA: 501

    # Test that if no data is provided it returns empty lists
    assert convert_currencies_from_list({}, field, currencies, default_currency, [], [], "", [], curr_convert) == ([], [], "", [])  # NOQA: 501


def test_convert_currencies_from_dict(mocker, fixture_currencies):
    # convert result for convert({value: 1, 'value.currency': 'EUR'}, currencies, 'USD', 'USD')
    convert_ex_res = (1.0705273292815591, 0.9341190763164442, 'EUR')  # Values based on fixture_currencies euro to gbp
    # mock convert to return convert ex res
    mock_convert = mocker.patch('direct_indexing.custom_fields.currency_conversion.convert', return_value=convert_ex_res)  # NOQA: 501
    data = {"budget": {}}
    field = "budget"
    currencies = fixture_currencies
    default_currency = None
    curr_convert = 'USD'

    ex_res = ([convert_ex_res[0]], [convert_ex_res[1]], convert_ex_res[2], [])
    assert convert_currencies_from_dict(data, field, currencies, default_currency, [], [], [], curr_convert) == ex_res
    mock_convert.assert_called_once()

    # Test that if the field is transaction, the transaction type code is added to t_type
    field = "transaction"
    data = {"transaction": {"transaction-type": {"code": "11"}}}
    ex_res = ([convert_ex_res[0]], [convert_ex_res[1]], convert_ex_res[2], ["11"])
    assert convert_currencies_from_dict(data, field, currencies, default_currency, [], [], [], curr_convert) == ex_res

    # Test that if no data is provided it returns empty lists
    assert convert_currencies_from_dict({}, field, currencies, default_currency, [], [], [], curr_convert) == ([], [], "", [])  # NOQA: 501


def test_convert(mocker, fixture_currencies):
    # Sample usage convert(data[field], currencies, default_currency=default_currency, target_currency=curr_convert)
    currencies = fixture_currencies
    default_currency = None
    target_currency = 'USD'
    value = 'value'

    empty_res = (None, None, None)
    # Test that if no value is provided we return None
    assert convert({}, currencies, default_currency, target_currency) == empty_res

    # Test that if no currency nor default currency is provided we return None
    assert convert({value: 1}, currencies, default_currency, target_currency) == empty_res

    # Test that if get_ym returns None, this function returns None
    mock_ym = mocker.patch('direct_indexing.custom_fields.currency_conversion.get_ym')
    mock_ym.return_value = (None, None)
    assert convert({value: 1}, currencies, 'EUR', target_currency) == empty_res

    # Test that if a value.currency is provided, it returns the correct converted value, rate and currency
    mock_ym.return_value = (2023, 3)
    ex_res = (1.0705273292815591, 0.9341190763164442, 'EUR')  # Values based on fixture_currencies euro to gbp
    assert convert({value: 1, 'value.currency': 'EUR'}, currencies, default_currency, target_currency) == ex_res

    # Test that if a default currency is provided, it returns the correct converted value, rate and currency
    assert convert({value: 1}, currencies, 'EUR', target_currency) == ex_res

    # Test that if a different value.currency to default currency is provided, it uses the value.currency
    assert convert({value: 1, 'value.currency': 'EUR'}, currencies, 'CAD', target_currency) == ex_res


def test_get_ym():
    now = datetime.now()
    vvd = 'value.value-date'
    sample_date = '2019-03-31T00:00:00Z'
    malformed_date = '31-03-2019'
    future_year = '9999-03-31T00:00:00Z'
    fm = now.month + 1
    if fm < 10:
        fm = "0" + str(fm)
    future_month = f'{now.year}-{fm}-31T00:00:00Z'
    empty_res = (None, None)

    # Test that if no date is provided, it returns None
    assert get_ym({}) == empty_res
    assert get_ym({vvd: ''}) == empty_res
    assert get_ym({vvd: malformed_date}) == empty_res

    assert get_ym({vvd: sample_date}) == (2019, 3)
    # Assert that if the year is in the future
    assert get_ym({vvd: future_year}) == (now.year, now.month)
    # Assert that if the month is in the future
    assert get_ym({vvd: future_month}) == (now.year, now.month)


def test_save_converted_value_to_data():
    # Sample usage: save_converted_value_to_data(data, value, field, rate, first_currency, t_type, curr_convert)
    value = [1, 2]
    field = 'transaction'
    rate = '1.2'
    first_currency = 'EUR'
    t_type = '1'
    curr_convert = 'GBP'
    expected_res = {
        'transaction.value-GBP': value,
        'transaction.value-GBP.sum': sum(value),
        'transaction.value-GBP.conversion-rate': rate,
        'transaction.value-GBP.conversion-currency': first_currency,
        'transaction.value-GBP-type': t_type,
    }
    assert save_converted_value_to_data({}, value, field, rate, first_currency, t_type, curr_convert) == expected_res


@pytest.fixture
def fixture_currencies(monkeypatch):
    data = [
        {
            "year": 2023,
            "month": 3,
            "currency_id": "DZD",
            "value": 0.0055024487
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "AUD",
            "value": 0.5004460909
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "BRL",
            "value": 0.1435369091
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "BND",
            "value": 0.5580111364
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "CAD",
            "value": 0.5469695455
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "CLP",
            "value": 0.0009245674
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "CNY",
            "value": 0.1084970435
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "CZK",
            "value": 0.0338277913
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "DKK",
            "value": 0.1075872609
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "EUR",
            "value": 0.8010585652
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "INR",
            "value": 0.009096549
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "ILS",
            "value": 0.2065905714
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "JPY",
            "value": 0.0055926118
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "KWD",
            "value": 2.4406338889
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "MYR",
            "value": 0.167557
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "MUR",
            "value": 0.0160274591
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "MXN",
            "value": 0.0407320857
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "NZD",
            "value": 0.4642263478
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "NOK",
            "value": 0.070986187
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "OMR",
            "value": 1.9457838889
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "PEN",
            "value": 0.1980674545
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "PHP",
            "value": 0.0136560478
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "PLN",
            "value": 0.1707347143
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "QAR",
            "value": 0.2055417778
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "RUB",
            "value": 0.0098281315
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "SGD",
            "value": 0.5580978696
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "ZAR",
            "value": 0.0409649182
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "SEK",
            "value": 0.0714488217
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "CHF",
            "value": 0.8084539565
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "THB",
            "value": 0.0216839455
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "TTD",
            "value": 0.1108243333
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "AED",
            "value": 0.2036608235
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "GBP",
            "value": 0.9081411304
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "USD",
            "value": 0.748284087
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "UYU",
            "value": 0.0191300048
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "BWP",
            "value": 0.0564973381
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "KRW",
            "value": 0.0005730496
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "SAR",
            "value": 0.1994885882
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "KZT",
            "value": 0.00164567
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "PKR",
            "value": 0.00261976
        },
        {
            "year": 2023,
            "month": 3,
            "currency_id": "LKR",
            "value": 0.00227131
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "DZD",
            "value": 0.0054729772
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "AUD",
            "value": 0.4962634706
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "BWP",
            "value": 0.0563683588
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "BRL",
            "value": 0.1477044444
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "BND",
            "value": 0.5565637222
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "CAD",
            "value": 0.5496927778
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "CLP",
            "value": 0.0009223087
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "CNY",
            "value": 0.1076211053
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "CZK",
            "value": 0.0346886611
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "DKK",
            "value": 0.1091274706
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "EUR",
            "value": 0.8129906111
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "INR",
            "value": 0.0090398547
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "ILS",
            "value": 0.2037545714
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "JPY",
            "value": 0.005560194
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "KRW",
            "value": 0.0005616467
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "KWD",
            "value": 2.4214066667
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "MYR",
            "value": 0.1676217222
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "MUR",
            "value": 0.016357335
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "MXN",
            "value": 0.0409774647
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "NZD",
            "value": 0.4605645882
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "NOK",
            "value": 0.0705617588
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "OMR",
            "value": 1.92819
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "PEN",
            "value": 0.1970261111
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "PHP",
            "value": 0.0134014063
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "PLN",
            "value": 0.1754046111
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "QAR",
            "value": 0.2038464
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "RUB",
            "value": 0.00913358
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "SAR",
            "value": 0.1977257273
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "SGD",
            "value": 0.5565551579
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "ZAR",
            "value": 0.0407851294
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "SEK",
            "value": 0.0717207444
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "CHF",
            "value": 0.8259735556
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "THB",
            "value": 0.0216301824
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "TTD",
            "value": 0.1097627647
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "AED",
            "value": 0.201902875
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "GBP",
            "value": 0.9228205556
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "USD",
            "value": 0.74132105
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "UYU",
            "value": 0.0191143824
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "BHD",
            "value": 1.97401
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "COP",
            "value": 0.000159511
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "HUF",
            "value": 0.00218767
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "ISK",
            "value": 0.00546757
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "IDR",
            "value": 5.03278e-05
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "IRR",
            "value": 2.9695e-06
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "KZT",
            "value": 0.00163741
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "LYD",
            "value": 0.155499
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "NPR",
            "value": 0.0056701
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "PKR",
            "value": 0.00261554
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "LKR",
            "value": 0.00230806
        },
        {
            "year": 2023,
            "month": 4,
            "currency_id": "TND",
            "value": 0.24411
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "AUD",
            "value": 0.4962168182
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "CAD",
            "value": 0.5515419048
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "ILS",
            "value": 0.2036497143
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "JPY",
            "value": 0.0054415732
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "KWD",
            "value": 2.4304116667
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "NZD",
            "value": 0.4640680909
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "OMR",
            "value": 1.9390566667
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "QAR",
            "value": 0.2048260556
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "SAR",
            "value": 0.1988177778
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "TTD",
            "value": 0.1103666667
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "AED",
            "value": 0.2030133333
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "USD",
            "value": 0.7456007727
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "DZD",
            "value": 0.0054857624
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "BWP",
            "value": 0.05536733
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "BRL",
            "value": 0.1497138571
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "BND",
            "value": 0.5570951429
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "CLP",
            "value": 0.00093417
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "CZK",
            "value": 0.034354895
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "DKK",
            "value": 0.1088746667
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "EUR",
            "value": 0.8109615238
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "INR",
            "value": 0.00906147
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "KRW",
            "value": 0.0005617361
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "MUR",
            "value": 0.0163771571
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "MXN",
            "value": 0.0420284571
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "NOK",
            "value": 0.0692027316
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "PEN",
            "value": 0.202329
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "PHP",
            "value": 0.0133836476
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "PLN",
            "value": 0.1787335
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "RUB",
            "value": 0.0094186205
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "SGD",
            "value": 0.5570951429
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "ZAR",
            "value": 0.0392001571
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "SEK",
            "value": 0.071512965
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "CHF",
            "value": 0.83149215
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "THB",
            "value": 0.0218094421
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "GBP",
            "value": 0.93116545
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "UYU",
            "value": 0.019186505
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "CNY",
            "value": 0.1066788421
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "MYR",
            "value": 0.1648854706
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "KZT",
            "value": 0.00168102
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "PKR",
            "value": 0.00263966
        },
        {
            "year": 2023,
            "month": 5,
            "currency_id": "LKR",
            "value": 0.00254911
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "DZD",
            "value": 0.0055142767
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "AUD",
            "value": 0.5022857895
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "BWP",
            "value": 0.05569348
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "BRL",
            "value": 0.15451
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "BND",
            "value": 0.557055875
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "CAD",
            "value": 0.5641984
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "CLP",
            "value": 0.0009364994
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "CNY",
            "value": 0.1047169474
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "CZK",
            "value": 0.034299745
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "DKK",
            "value": 0.1091807895
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "EUR",
            "value": 0.8124538571
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "INR",
            "value": 0.0091159728
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "ILS",
            "value": 0.20559615
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "JPY",
            "value": 0.005312709
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "KRW",
            "value": 0.0005778121
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "KWD",
            "value": 2.4416108333
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "MYR",
            "value": 0.1616965556
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "MUR",
            "value": 0.0163719105
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "MXN",
            "value": 0.043475255
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "NZD",
            "value": 0.4594601053
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "NOK",
            "value": 0.069311425
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "OMR",
            "value": 1.9510592857
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "PEN",
            "value": 0.2054745294
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "PHP",
            "value": 0.0134161833
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "PLN",
            "value": 0.1821163684
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "QAR",
            "value": 0.2056876
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "RUB",
            "value": 0.0089449978
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "SAR",
            "value": 0.2000289167
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "SGD",
            "value": 0.5567785
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "ZAR",
            "value": 0.0399219526
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "SEK",
            "value": 0.0696344389
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "CHF",
            "value": 0.8321152381
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "THB",
            "value": 0.0214739722
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "TTD",
            "value": 0.1110543333
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "AED",
            "value": 0.2041703333
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "GBP",
            "value": 0.9459971905
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "USD",
            "value": 0.749791
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "UYU",
            "value": 0.019643545
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "PKR",
            "value": 0.00261539
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "KZT",
            "value": 0.00166148
        },
        {
            "year": 2023,
            "month": 6,
            "currency_id": "LKR",
            "value": 0.00243447
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "AUD",
            "value": 0.5015182632
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "BWP",
            "value": 0.0563089412
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "BRL",
            "value": 0.1548863684
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "BND",
            "value": 0.5577022778
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "CAD",
            "value": 0.5626279474
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "CLP",
            "value": 0.000912668
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "CNY",
            "value": 0.1034731053
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "DKK",
            "value": 0.1105018947
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "EUR",
            "value": 0.8233651579
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "INR",
            "value": 0.0090472889
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "ILS",
            "value": 0.2029819444
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "JPY",
            "value": 0.0052815311
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "KRW",
            "value": 0.0005793915
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "KWD",
            "value": 2.42472
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "MYR",
            "value": 0.1620822222
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "MUR",
            "value": 0.0162544158
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "MXN",
            "value": 0.0440186526
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "NZD",
            "value": 0.4633512222
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "NOK",
            "value": 0.0727839421
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "OMR",
            "value": 1.9345584615
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "PEN",
            "value": 0.2069064706
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "PHP",
            "value": 0.0135471056
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "PLN",
            "value": 0.1852460526
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "QAR",
            "value": 0.204225
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "RUB",
            "value": 0.0081926668
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "SAR",
            "value": 0.1982345333
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "SGD",
            "value": 0.5577778947
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "ZAR",
            "value": 0.0410038842
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "SEK",
            "value": 0.0708933526
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "CHF",
            "value": 0.8534652105
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "THB",
            "value": 0.0215029944
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "TTD",
            "value": 0.1101218947
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "AED",
            "value": 0.202471
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "GBP",
            "value": 0.9592823684
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "USD",
            "value": 0.7434777368
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "UYU",
            "value": 0.0196081444
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "DZD",
            "value": 0.0055074706
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "CZK",
            "value": 0.0344431059
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "KZT",
            "value": 0.00166933
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "PKR",
            "value": 0.00259571
        },
        {
            "year": 2023,
            "month": 7,
            "currency_id": "LKR",
            "value": 0.00226088
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "DZD",
            "value": 0.0055146809
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "AUD",
            "value": 0.4868466364
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "BWP",
            "value": 0.055647587
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "BRL",
            "value": 0.1530352174
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "BND",
            "value": 0.5556082273
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "CAD",
            "value": 0.5564543182
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "CLP",
            "value": 0.0008768502
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "CNY",
            "value": 0.1034427826
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "CZK",
            "value": 0.0339419087
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "DKK",
            "value": 0.1098225652
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "EUR",
            "value": 0.818413087
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "INR",
            "value": 0.0090619629
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "ILS",
            "value": 0.200313
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "JPY",
            "value": 0.0051832405
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "KRW",
            "value": 0.0005691091
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "KWD",
            "value": 2.4387352632
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "MYR",
            "value": 0.1628059545
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "MUR",
            "value": 0.0164496174
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "MXN",
            "value": 0.0441962565
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "NZD",
            "value": 0.4501691739
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "NOK",
            "value": 0.071726713
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "OMR",
            "value": 1.9510936842
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "PEN",
            "value": 0.2031505
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "PHP",
            "value": 0.0133565381
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "PLN",
            "value": 0.1835320909
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "QAR",
            "value": 0.2060975263
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "RUB",
            "value": 0.00786002
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "SAR",
            "value": 0.2000377778
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "SGD",
            "value": 0.5556082273
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "ZAR",
            "value": 0.0400104545
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "SEK",
            "value": 0.0693934045
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "AED",
            "value": 0.2042737368
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "GBP",
            "value": 0.953221
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "USD",
            "value": 0.750241087
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "UYU",
            "value": 0.0198174182
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "CHF",
            "value": 0.8538547727
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "THB",
            "value": 0.0214139476
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "TTD",
            "value": 0.1112321429
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "KZT",
            "value": 0.0016357
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "PKR",
            "value": 0.00246031
        },
        {
            "year": 2023,
            "month": 8,
            "currency_id": "LKR",
            "value": 0.00233033
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "DZD",
            "value": 0.00553097
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "AUD",
            "value": 0.48688025
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "BWP",
            "value": 0.055502375
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "BRL",
            "value": 0.1535732105
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "CAD",
            "value": 0.5599346316
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "CLP",
            "value": 0.0008556479
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "CNY",
            "value": 0.1038478421
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "DKK",
            "value": 0.10856035
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "EUR",
            "value": 0.80951055
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "INR",
            "value": 0.0091232659
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "ILS",
            "value": 0.1983924444
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "JPY",
            "value": 0.0051312216
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "KRW",
            "value": 0.0005697273
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "MYR",
            "value": 0.1619180526
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "MUR",
            "value": 0.0167957579
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "MXN",
            "value": 0.04379213
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "NZD",
            "value": 0.44912815
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "NOK",
            "value": 0.070701
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "PEN",
            "value": 0.2032994211
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "PLN",
            "value": 0.17586925
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "RUB",
            "value": 0.0078457025
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "ZAR",
            "value": 0.0399287947
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "SEK",
            "value": 0.0683663
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "CHF",
            "value": 0.8432669
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "THB",
            "value": 0.021131905
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "TTD",
            "value": 0.11244325
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "GBP",
            "value": 0.93914965
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "USD",
            "value": 0.7581312
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "UYU",
            "value": 0.0198647158
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "BND",
            "value": 0.5559153889
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "CZK",
            "value": 0.0331536722
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "KWD",
            "value": 2.4562335714
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "OMR",
            "value": 1.9709521429
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "PHP",
            "value": 0.0133545842
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "QAR",
            "value": 0.2083222667
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "SAR",
            "value": 0.2022114
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "SGD",
            "value": 0.5559168947
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "AED",
            "value": 0.206395
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "LKR",
            "value": 0.00235056
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "PKR",
            "value": 0.00264992
        },
        {
            "year": 2023,
            "month": 9,
            "currency_id": "KZT",
            "value": 0.00160278
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "DZD",
            "value": 0.0055493914
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "BRL",
            "value": 0.149033
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "BND",
            "value": 0.5570754286
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "CLP",
            "value": 0.0008356787
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "CZK",
            "value": 0.0328431429
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "DKK",
            "value": 0.1077734286
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "EUR",
            "value": 0.803745
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "ILS",
            "value": 0.1965672857
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "JPY",
            "value": 0.0051166829
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "KWD",
            "value": 2.4685933333
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "MYR",
            "value": 0.1614551429
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "MUR",
            "value": 0.0171297286
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "MXN",
            "value": 0.0424532714
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "NZD",
            "value": 0.4555665714
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "NOK",
            "value": 0.0699529857
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "OMR",
            "value": 1.9845675
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "PEN",
            "value": 0.2001476667
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "PHP",
            "value": 0.0134337286
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "PLN",
            "value": 0.1752022857
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "QAR",
            "value": 0.2095483333
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "RUB",
            "value": 0.00765667
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "SAR",
            "value": 0.2034015
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "SGD",
            "value": 0.5570754286
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "ZAR",
            "value": 0.0397042571
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "SEK",
            "value": 0.0693457429
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "CHF",
            "value": 0.8352217143
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "THB",
            "value": 0.0206688286
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "TTD",
            "value": 0.1131596667
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "AED",
            "value": 0.2076938333
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "GBP",
            "value": 0.9286597143
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "USD",
            "value": 0.7626655714
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "UYU",
            "value": 0.0193836667
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "AUD",
            "value": 0.4856458333
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "CAD",
            "value": 0.5572896
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "INR",
            "value": 0.00916226
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "BWP",
            "value": 0.0551175
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "KRW",
            "value": 0.0005638912
        },
        {
            "year": 2023,
            "month": 10,
            "currency_id": "CNY",
            "value": 0.104258
        }
    ]
    # mock codelists class init to set self.codelists_dict to `data`
    monkeypatch.setattr(currencies.Currencies, "__init__", lambda x: setattr(x, "currencies_list", data))
    return currencies.Currencies()
