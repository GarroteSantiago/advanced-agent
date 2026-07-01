"""Tests for the events subsystem: bus, subscriptions, and audit logger."""

from harness.events import (
        AuditLogger,
        EventBus,
        EventHandler,
        PhaseCompleted,
        PhaseStarted,
        ToolObserved,
)


def test_events_carry_their_fields_and_a_timestamp():
        event = ToolObserved(tool_name="echo", call_id="c1", ok=True)
        assert event.tool_name == "echo"
        assert event.ok is True
        assert event.occurred_at is not None


def test_distinct_event_types_are_not_equal_even_with_same_fields():
        assert PhaseStarted(phase="reason") != PhaseCompleted(phase="reason")


def test_bus_delivers_published_events_to_all_subscribers():
        first, second = AuditLogger(), AuditLogger()
        bus = EventBus()
        bus.subscribe(first)
        bus.subscribe(second)

        event = PhaseStarted(phase="reason")
        bus.publish(event)

        assert first.records() == (event,)
        assert second.records() == (event,)


def test_cancelled_subscription_stops_receiving():
        logger = AuditLogger()
        bus = EventBus()
        subscription = bus.subscribe(logger)

        bus.publish(PhaseStarted(phase="reason"))
        subscription.cancel()
        bus.publish(PhaseCompleted(phase="reason"))

        assert [type(e) for e in logger.records()] == [PhaseStarted]
        assert subscription.active is False


def test_cancel_is_idempotent():
        bus = EventBus()
        subscription = bus.subscribe(AuditLogger())
        subscription.cancel()
        subscription.cancel()  # must not raise
        assert subscription.active is False


def test_audit_logger_records_in_order_and_view_is_immutable():
        logger = AuditLogger()
        logger.handle(PhaseStarted(phase="reason"))
        logger.handle(PhaseCompleted(phase="reason"))

        records = logger.records()
        assert [type(e) for e in records] == [PhaseStarted, PhaseCompleted]
        assert isinstance(records, tuple)


def test_audit_logger_conforms_to_event_handler_port():
        handler: EventHandler = AuditLogger()
        assert isinstance(handler, EventHandler)
