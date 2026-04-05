import { useState, useMemo, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { ChevronLeft, ChevronRight } from "lucide-react";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function CalendarView() {
  const { state, dispatch } = useApp();
  const [currentDate, setCurrentDate] = useState(new Date());

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // Get all daily notes mapped by date string
  const dailyNotes = useMemo(() => {
    const map = new Map<string, string>();
    for (const note of state.notes) {
      if (note.file_path.startsWith("daily/")) {
        const dateStr = note.file_path.replace("daily/", "").replace(".md", "");
        map.set(dateStr, note.id);
      }
    }
    return map;
  }, [state.notes]);

  // Generate calendar grid
  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrevMonth = new Date(year, month, 0).getDate();

    const days: { date: number; month: number; year: number; isCurrentMonth: boolean; dateStr: string }[] = [];

    // Previous month padding
    for (let i = firstDay - 1; i >= 0; i--) {
      const d = daysInPrevMonth - i;
      const m = month === 0 ? 11 : month - 1;
      const y = month === 0 ? year - 1 : year;
      days.push({
        date: d,
        month: m,
        year: y,
        isCurrentMonth: false,
        dateStr: `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`,
      });
    }

    // Current month
    for (let d = 1; d <= daysInMonth; d++) {
      days.push({
        date: d,
        month,
        year,
        isCurrentMonth: true,
        dateStr: `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`,
      });
    }

    // Next month padding (fill to 42 = 6 rows)
    const remaining = 42 - days.length;
    for (let d = 1; d <= remaining; d++) {
      const m = month === 11 ? 0 : month + 1;
      const y = month === 11 ? year + 1 : year;
      days.push({
        date: d,
        month: m,
        year: y,
        isCurrentMonth: false,
        dateStr: `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`,
      });
    }

    return days;
  }, [year, month]);

  const today = useMemo(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  }, []);

  const prevMonth = useCallback(() => {
    setCurrentDate(new Date(year, month - 1, 1));
  }, [year, month]);

  const nextMonth = useCallback(() => {
    setCurrentDate(new Date(year, month + 1, 1));
  }, [year, month]);

  const goToToday = useCallback(() => {
    setCurrentDate(new Date());
  }, []);

  const handleDayClick = useCallback(
    async (dateStr: string) => {
      const noteId = dailyNotes.get(dateStr);
      if (noteId) {
        dispatch({ type: "SET_ACTIVE_NOTE", id: noteId });
        dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
      } else {
        // Create daily note for that date
        try {
          const filePath = `daily/${dateStr}.md`;
          const note = await api.saveNote(
            filePath,
            dateStr,
            `# ${dateStr}\n\n## Journal\n\n\n\n## Tasks\n\n- [ ] \n\n`,
            { date: dateStr, type: "daily" }
          );
          dispatch({ type: "UPDATE_NOTE", note });
          dispatch({ type: "SET_ACTIVE_NOTE", id: note.id });
          dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
        } catch (err) {
          console.error("Failed to create note for date:", err);
        }
      }
    },
    [dailyNotes, dispatch]
  );

  // Count notes created per day (not just daily notes)
  const noteCountByDate = useMemo(() => {
    const counts = new Map<string, number>();
    for (const note of state.notes) {
      const date = note.created_at.slice(0, 10);
      counts.set(date, (counts.get(date) ?? 0) + 1);
    }
    return counts;
  }, [state.notes]);

  return (
    <div className="main-content">
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <span>Calendar</span>
        </div>
        <div className="editor-actions">
          <button className="icon-btn" onClick={goToToday} title="Today">
            <span style={{ fontSize: 11 }}>Today</span>
          </button>
        </div>
      </div>

      <div className="calendar-wrapper">
        <div className="calendar-nav">
          <button className="icon-btn" onClick={prevMonth}>
            <ChevronLeft size={16} />
          </button>
          <h2 className="calendar-title">
            {MONTHS[month]} {year}
          </h2>
          <button className="icon-btn" onClick={nextMonth}>
            <ChevronRight size={16} />
          </button>
        </div>

        <div className="calendar-grid">
          {DAYS.map((day) => (
            <div key={day} className="calendar-day-header">
              {day}
            </div>
          ))}
          {calendarDays.map((day, i) => {
            const hasDaily = dailyNotes.has(day.dateStr);
            const noteCount = noteCountByDate.get(day.dateStr) ?? 0;
            const isToday = day.dateStr === today;

            return (
              <div
                key={i}
                className={[
                  "calendar-day",
                  !day.isCurrentMonth && "other-month",
                  isToday && "today",
                  hasDaily && "has-note",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => handleDayClick(day.dateStr)}
              >
                <span className="calendar-day-number">{day.date}</span>
                {hasDaily && <div className="calendar-dot" />}
                {noteCount > 0 && !hasDaily && (
                  <div className="calendar-count">{noteCount}</div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
