import pytest

@pytest.fixture
def username():
    print("\n前置准备数据")
    yield 'summer'
    print("\n后置清理数据")