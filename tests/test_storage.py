"""Tests for storage module."""
import pytest
import tempfile
import os

from thirdlayer_prototype.db.storage import Storage
from thirdlayer_prototype.models.action import navigate, click, type_text


@pytest.fixture
def temp_storage():
    """Create temporary storage for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    storage = Storage(path)
    storage.connect()
    
    yield storage
    
    storage.close()
    os.unlink(path)


def test_storage_initialization(temp_storage):
    """Test database initialization and schema creation."""
    cursor = temp_storage.conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "actions" in tables
    assert "transitions_first_order" in tables
    assert "transitions_second_order" in tables


def test_record_action(temp_storage):
    """Test recording single action."""
    action = navigate("https://example.com")
    
    action_id = temp_storage.record_action(action, url="https://example.com")
    
    assert action_id > 0
    
    recent = temp_storage.get_recent_actions(limit=1)
    assert len(recent) == 1
    assert recent[0].signature() == action.signature()


def test_record_first_order_transition(temp_storage):
    """Test recording first-order transition."""
    action1 = navigate("https://example.com")
    action2 = click("#button")
    
    temp_storage.record_transition_first_order(action1, action2)
    
    transitions = temp_storage.get_first_order_transitions(action1)
    
    assert len(transitions) == 1
    assert transitions[0]["count"] == 1


def test_record_second_order_transition(temp_storage):
    """Test recording second-order transition."""
    action1 = navigate("https://example.com")
    action2 = click("#button")
    action3 = type_text("#input", "test")
    
    temp_storage.record_transition_second_order(action1, action2, action3)
    
    transitions = temp_storage.get_second_order_transitions(action1, action2)
    
    assert len(transitions) == 1
    assert transitions[0]["count"] == 1


def test_transition_count_increment(temp_storage):
    """Test that repeated transitions increment count."""
    action1 = navigate("https://example.com")
    action2 = click("#button")
    
    temp_storage.record_transition_first_order(action1, action2)
    temp_storage.record_transition_first_order(action1, action2)
    temp_storage.record_transition_first_order(action1, action2)
    
    transitions = temp_storage.get_first_order_transitions(action1)
    
    assert len(transitions) == 1
    assert transitions[0]["count"] == 3


def test_get_top_transitions(temp_storage):
    """Test getting top transitions."""
    action1 = navigate("https://example.com")
    action2 = click("#button1")
    action3 = click("#button2")
    
    temp_storage.record_transition_first_order(action1, action2)
    temp_storage.record_transition_first_order(action1, action2)
    temp_storage.record_transition_first_order(action1, action3)
    
    top = temp_storage.get_top_transitions(k=10)
    
    assert len(top) == 2
    assert top[0]["count"] == 2
    assert top[1]["count"] == 1
