import asyncio
import EventKit
from datetime import datetime
from typing import Optional

class CalendarClient:
    def __init__(self):
        self.store = EventKit.EKEventStore.alloc().init()
        self._authorized = False

    async def request_access(self):
        """Request access to the calendar and wait for the response."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def handler(granted, error):
            def resolve():
                self._authorized = granted
                if error:
                    print(f"Error requesting access: {error}")
                if not future.done():
                    future.set_result(granted)
            loop.call_soon_threadsafe(resolve)

        self.store.requestAccessToEntityType_completion_(
            EventKit.EKEntityTypeEvent,
            handler
        )

        granted = await asyncio.wait_for(future, timeout=10)
        if not granted:
            raise PermissionError("Calendar access was denied.")

    # --- Calendars ---

    def get_calendars(self) -> list:
        """Retrieve all available calendars."""
        calendars = self.store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
        return [{
            "id": c.calendarIdentifier(),
            "title": c.title(),
            "color": str(c.color()),
            "is_editable": c.allowsContentModifications()
        } for c in calendars]

    # --- Events ---

    def get_events(self, start: datetime, end: datetime, calendar_ids: Optional[list] = None) -> list:
        """Retrieve events between two dates, optionally filtered by calendar."""
        calendars = None
        if calendar_ids:
            all_calendars = self.store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
            calendars = [c for c in all_calendars if c.calendarIdentifier() in calendar_ids]

        predicate = self.store.predicateForEventsWithStartDate_endDate_calendars_(
            start, end, calendars
        )
        events = self.store.eventsMatchingPredicate_(predicate)
        return [self._serialize_event(e) for e in events]

    def get_event(self, event_id: str) -> Optional[dict]:
        """Retrieve a single event by its identifier."""
        event = self.store.eventWithIdentifier_(event_id)
        if event is None:
            return None
        return self._serialize_event(event)

    def search_events(self, query: str, start: datetime, end: datetime) -> list:
        """Search for events matching a keyword in their title."""
        all_events = self.get_events(start, end)
        return [e for e in all_events if query.lower() in e["title"].lower()]

    def create_event(
        self,
        title: str,
        start: datetime,
        end: datetime,
        calendar_id: Optional[str] = None,
        notes: Optional[str] = None,
        alarm_minutes_before: Optional[int] = None
    ) -> dict:
        """Create a new calendar event."""
        event = EventKit.EKEvent.eventWithEventStore_(self.store)
        event.setTitle_(title)
        event.setStartDate_(start)
        event.setEndDate_(end)

        if notes:
            event.setNotes_(notes)

        if calendar_id:
            all_calendars = self.store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
            calendar = next((c for c in all_calendars if c.calendarIdentifier() == calendar_id), None)
            event.setCalendar_(calendar or self.store.defaultCalendarForNewEvents())
        else:
            event.setCalendar_(self.store.defaultCalendarForNewEvents())

        if alarm_minutes_before is not None:
            alarm = EventKit.EKAlarm.alarmWithRelativeOffset_(-alarm_minutes_before * 60)
            event.addAlarm_(alarm)

        error = None
        success = self.store.saveEvent_span_error_(event, EventKit.EKSpanThisEvent, error)
        if not success:
            raise RuntimeError(f"Failed to save event: {error}")

        return self._serialize_event(event)

    def update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        notes: Optional[str] = None,
        calendar_id: Optional[str] = None
    ) -> dict:
        """Update an existing calendar event."""
        event = self.store.eventWithIdentifier_(event_id)
        if event is None:
            raise ValueError(f"Event not found: {event_id}")

        if title:
            event.setTitle_(title)
        if start:
            event.setStartDate_(start)
        if end:
            event.setEndDate_(end)
        if notes:
            event.setNotes_(notes)
        if calendar_id:
            all_calendars = self.store.calendarsForEntityType_(EventKit.EKEntityTypeEvent)
            calendar = next((c for c in all_calendars if c.calendarIdentifier() == calendar_id), None)
            if calendar:
                event.setCalendar_(calendar)

        error = None
        success = self.store.saveEvent_span_error_(event, EventKit.EKSpanThisEvent, error)
        if not success:
            raise RuntimeError(f"Failed to update event: {error}")

        return self._serialize_event(event)

    def delete_event(self, event_id: str) -> bool:
        """Delete an event by its identifier."""
        event = self.store.eventWithIdentifier_(event_id)
        if event is None:
            raise ValueError(f"Event not found: {event_id}")

        error = None
        success = self.store.removeEvent_span_error_(event, EventKit.EKSpanThisEvent, error)
        if not success:
            raise RuntimeError(f"Failed to delete event: {error}")

        return True

    def add_alarm(self, event_id: str, minutes_before: int) -> dict:
        """Add an alarm to an existing event."""
        event = self.store.eventWithIdentifier_(event_id)
        if event is None:
            raise ValueError(f"Event not found: {event_id}")

        alarm = EventKit.EKAlarm.alarmWithRelativeOffset_(-minutes_before * 60)
        event.addAlarm_(alarm)

        error = None
        success = self.store.saveEvent_span_error_(event, EventKit.EKSpanThisEvent, error)
        if not success:
            raise RuntimeError(f"Failed to add alarm: {error}")

        return self._serialize_event(event)

    # --- Helpers ---

    def _serialize_event(self, event) -> dict:
        """Convert an EKEvent object to a dictionary."""
        alarms = []
        if event.alarms():
            alarms = [int(a.relativeOffset() / -60) for a in event.alarms()]

        return {
            "id": event.eventIdentifier(),
            "title": event.title(),
            "start": str(event.startDate()),
            "end": str(event.endDate()),
            "notes": event.notes() or "",
            "calendar_id": event.calendar().calendarIdentifier(),
            "calendar_title": event.calendar().title(),
            "is_all_day": event.isAllDay(),
            "alarms_minutes_before": alarms
        }