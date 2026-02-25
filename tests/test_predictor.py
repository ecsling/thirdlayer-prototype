"""Tests for predictor module."""
import pytest
import tempfile
import os

from thirdlayer_prototype.db.storage import Storage
from thirdlayer_prototype.agent.predictor import Predictor
from thirdlayer_prototype.models.action import navigate, click, type_text


@pytest.fixture
def storage_with_data():
    """Create storage with test data."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    storage = Storage(path)
    storage.connect()
    
    action1 = navigate("https://example.com")
    action2 = click("#button")
    action3 = type_text("#input", "test")
    
    storage.record_transition_first_order(action1, action2)
    storage.record_transition_first_order(action1, action2)
    storage.record_transition_first_order(action1, action3)
    
    storage.record_transition_second_order(action1, action2, action3)
    storage.record_transition_second_order(action1, action2, action3)
    
    yield storage
    
    storage.close()
    os.unlink(path)


def test_predict_first_order(storage_with_data):
    """Test first-order prediction."""
    predictor = Predictor(storage_with_data)
    
    action1 = navigate("https://example.com")
    predictions = predictor.predict_first_order(action1, k=5)
    
    assert len(predictions) == 2
    
    assert predictions[0].confidence > predictions[1].confidence
    
    assert predictions[0].confidence == pytest.approx(2/3, rel=0.01)
    assert predictions[1].confidence == pytest.approx(1/3, rel=0.01)


def test_predict_second_order(storage_with_data):
    """Test second-order prediction."""
    predictor = Predictor(storage_with_data)
    
    action1 = navigate("https://example.com")
    action2 = click("#button")
    predictions = predictor.predict_second_order(action1, action2, k=5)
    
    assert len(predictions) == 1
    assert predictions[0].confidence == 1.0
    assert predictions[0].source == "second_order"


def test_predict_fallback_to_first_order(storage_with_data):
    """Test that predict() falls back to first-order when second-order unavailable."""
    predictor = Predictor(storage_with_data)
    
    action1 = navigate("https://example.com")
    action_unknown = type_text("#unknown", "foo")
    
    predictions = predictor.predict(
        action_history=[action_unknown, action1],
        k=5,
        use_second_order=True,
    )
    
    assert len(predictions) == 2
    assert all(p.source == "first_order" for p in predictions)


def test_predict_no_history():
    """Test prediction with no action history."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    storage = Storage(path)
    storage.connect()
    predictor = Predictor(storage)
    
    predictions = predictor.predict(action_history=[], k=5)
    
    assert len(predictions) == 0
    
    storage.close()
    os.unlink(path)
