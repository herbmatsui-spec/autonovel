import pytest
import streamlit as st
from streamlit_app.state import UIStateStore, UIState

def test_ui_state_initialization():
    store = UIStateStore()
    assert isinstance(store.ui_state, UIState)
    assert store.ui_state.show_modal == False
    assert store.ui_state.active_tab == "home"

def test_update_ui_state():
    store = UIStateStore()
    store.update_ui_state(show_modal=True, custom_key="test_value")
    assert store.get_ui_state_value("show_modal") == True
    assert store.get_ui_state_value("custom_key") == "test_value"

def test_subscribe_notify():
    store = UIStateStore()
    called = []
    def callback(val):
        called.append(val)
    
    unsubscribe = UIStateStore.subscribe("test_key", callback)
    store.update_ui_state(test_key="hello")
    assert called == ["hello"]
    
    unsubscribe()
    store.update_ui_state(test_key="world")
    assert called == ["hello"]

def test_get_ui_state_value_default():
    store = UIStateStore()
    assert store.get_ui_state_value("nonexistent", "default") == "default"

def test_set_get_form_data():
    store = UIStateStore()
    store.set_form_data("my_form_field", "form_value")
    assert store.get_form_data("my_form_field") == "form_value"
    assert store.get_form_data("nonexistent", "default") == "default"

def test_reset_ui_state():
    store = UIStateStore()
    store.update_ui_state(show_modal=True, custom="value")
    store.reset_ui_state()
    assert store.get_ui_state_value("show_modal") == False
    assert store.get_ui_state_value("custom", "default") == "default"