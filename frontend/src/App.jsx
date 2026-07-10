import {
  Bot,
  CalendarDays,
  CheckCircle2,
  Clock3,
  Mic,
  PackagePlus,
  Search,
  TriangleAlert,
} from "lucide-react";
import React from "react";
import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import {
  appendUserMessage,
  fetchHcps,
  fetchInteractions,
  runToolsDemo,
  sendChat,
  submitInteraction,
} from "./store";

const initialForm = {
  hcp_name: "",
  date: "2025-04-19",
  time: "19:36",
  attendees: "",
  channel: "In-person",
  interaction_type: "Meeting",
  products_discussed: "CardioPlus",
  materials_shared: "",
  samples_distributed: "",
  sentiment: "Neutral",
  outcome: "",
  next_step: "",
  notes: "",
};

function App() {
  const dispatch = useDispatch();
  const { selectedHcpId, chat, lastResult, demoResult, status, error } = useSelector((state) => state.crm);
  const [form, setForm] = useState(initialForm);
  const [message, setMessage] = useState("");

  useEffect(() => {
    dispatch(fetchHcps());
    dispatch(fetchInteractions());
  }, [dispatch]);

  const updateForm = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    await dispatch(submitInteraction({ ...form, hcp_id: Number(selectedHcpId) }));
    dispatch(fetchInteractions());
  };

  const onSend = async (event) => {
    event.preventDefault();
    if (!message.trim()) return;
    dispatch(appendUserMessage(message));
    const result = await dispatch(sendChat({ message, hcp_id: Number(selectedHcpId) }));
    const patch = result.payload?.tool_output?.form_patch;
    if (patch) {
      setForm((current) => ({
        ...current,
        hcp_name: patch.hcp_name ?? current.hcp_name,
        date: patch.date ?? current.date,
        time: patch.time ?? current.time,
        attendees: patch.attendees ?? current.attendees,
        interaction_type: patch.interaction_type ?? current.interaction_type,
        products_discussed: patch.products_discussed ?? current.products_discussed,
        materials_shared: patch.materials_shared ?? current.materials_shared,
        samples_distributed: patch.samples_distributed ?? current.samples_distributed,
        sentiment: patch.sentiment ?? current.sentiment,
        outcome: patch.outcomes ?? current.outcome,
        next_step: patch.follow_up_actions ?? current.next_step,
        notes: patch.topics_discussed ?? current.notes,
      }));
    }
    setMessage("");
    dispatch(fetchInteractions());
  };

  return (
    <main className="page">
      <h1>Log HCP Interaction</h1>
      <section className="layout">
        <form className="detailsPanel" onSubmit={onSubmit}>
          <header className="panelHeader">
            <strong>Interaction Details</strong>
          </header>

          <div className="formGrid">
            <label className="field">
              <span>HCP Name</span>
              <input
                readOnly
                value={form.hcp_name}
                placeholder="Search or select HCP..."
              />
            </label>
            <label className="field">
              <span>Interaction Type</span>
              <select
                disabled
                value={form.interaction_type}
                onChange={(event) => updateForm("interaction_type", event.target.value)}
              >
                <option>Meeting</option>
                <option>Detailing</option>
                <option>Phone Call</option>
                <option>Virtual call</option>
                <option>Conference follow-up</option>
              </select>
            </label>
            <label className="field iconField">
              <span>Date</span>
              <input readOnly value={form.date} />
              <CalendarDays size={14} />
            </label>
            <label className="field iconField">
              <span>Time</span>
              <input readOnly value={form.time} />
              <Clock3 size={14} />
            </label>
          </div>

          <label className="field">
            <span>Attendees</span>
            <input readOnly value={form.attendees} placeholder="Enter names or search..." />
          </label>

          <label className="field textAreaField">
            <span>Topics Discussed</span>
            <textarea
              readOnly
              value={form.notes}
              placeholder="Enter key discussion points..."
              rows={4}
            />
            <Mic size={16} />
          </label>

          <button type="button" className="linkButton">
            <Mic size={15} />
            Summarize from Voice Note (Requires Consent)
          </button>

          <section className="miniSection">
            <h2>Materials Shared / Samples Distributed</h2>
            <div className="miniBox">
              <div>
                <strong>Materials Shared</strong>
                <em>{form.materials_shared || "No materials added."}</em>
              </div>
              <button type="button">
                <Search size={14} />
                Search/Add
              </button>
            </div>
            <div className="miniBox">
              <div>
                <strong>Samples Distributed</strong>
                <em>{form.samples_distributed || "No samples added."}</em>
              </div>
              <button type="button">
                <PackagePlus size={14} />
                Add Sample
              </button>
            </div>
          </section>

          <fieldset className="sentiment">
            <legend>Observed/Inferred HCP Sentiment</legend>
            {["Positive", "Neutral", "Negative"].map((item) => (
              <label key={item}>
                <input
                  type="radio"
                  name="sentiment"
                  readOnly
                  checked={form.sentiment === item}
                  onChange={() => {}}
                />
                {item}
              </label>
            ))}
          </fieldset>

          <label className="field">
            <span>Outcomes</span>
            <textarea
              readOnly
              value={form.outcome}
              placeholder="Key outcomes or agreements..."
              rows={3}
            />
          </label>

          <label className="field">
            <span>Follow-up Actions</span>
            <textarea
              readOnly
              value={form.next_step}
              placeholder="Enter next steps or tasks..."
              rows={3}
            />
          </label>

          <div className="suggestions">
            <strong>AI Suggested Follow-ups:</strong>
            <button type="button" onClick={() => dispatch(runToolsDemo())}>
              <CheckCircle2 size={14} />
              Schedule follow-up meeting in 2 weeks
            </button>
          </div>

          <button className="saveButton" disabled={status === "saving"}>
            {status === "saving" ? "Logging..." : "Save Interaction"}
          </button>
        </form>

        <aside className="assistantPanel">
          <header>
            <Bot size={18} />
            <div>
              <strong>AI Assistant</strong>
              <span>Log interaction via chat</span>
            </div>
          </header>

          <div className="assistantBody">
            {chat.map((item, index) => (
              <div key={`${item.role}-${index}`} className={`bubble ${item.role}`}>
                {item.text}
              </div>
            ))}
            {lastResult && <pre>{JSON.stringify(lastResult, null, 2)}</pre>}
            {demoResult && <pre>{JSON.stringify(demoResult, null, 2)}</pre>}
          </div>

          <form className="chatLogBar" onSubmit={onSend}>
            <input
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder='Try: Today I met with Dr. Smith and discussed product X efficacy. Sentiment was positive and I shared brochures.'
            />
            <button disabled={status === "thinking"}>
              <TriangleAlert size={15} />
              Log
            </button>
          </form>
        </aside>
      </section>
      {error && <p className="error">{error}</p>}
    </main>
  );
}

export default App;
