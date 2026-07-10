import { configureStore, createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { api } from "./api";

export const fetchHcps = createAsyncThunk("crm/fetchHcps", api.getHcps);
export const fetchInteractions = createAsyncThunk("crm/fetchInteractions", api.getInteractions);
export const submitInteraction = createAsyncThunk("crm/submitInteraction", api.logInteraction);
export const sendChat = createAsyncThunk("crm/sendChat", api.chat);
export const runToolsDemo = createAsyncThunk("crm/runToolsDemo", api.toolsDemo);

const initialState = {
  mode: "form",
  hcps: [],
  interactions: [],
  chat: [
    {
      role: "assistant",
      text: "Tell me what happened with the HCP. I can log, edit, check compliance, suggest next action, or schedule follow-up.",
    },
  ],
  selectedHcpId: 1,
  lastResult: null,
  demoResult: null,
  status: "idle",
  error: "",
};

const crmSlice = createSlice({
  name: "crm",
  initialState,
  reducers: {
    setMode(state, action) {
      state.mode = action.payload;
    },
    setSelectedHcpId(state, action) {
      state.selectedHcpId = Number(action.payload);
    },
    appendUserMessage(state, action) {
      state.chat.push({ role: "user", text: action.payload });
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHcps.fulfilled, (state, action) => {
        state.hcps = action.payload;
        if (action.payload[0]) state.selectedHcpId = action.payload[0].id;
      })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.interactions = action.payload;
      })
      .addCase(submitInteraction.pending, (state) => {
        state.status = "saving";
        state.error = "";
      })
      .addCase(submitInteraction.fulfilled, (state, action) => {
        state.status = "saved";
        state.lastResult = action.payload;
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.status = "error";
        state.error = action.error.message;
      })
      .addCase(sendChat.pending, (state) => {
        state.status = "thinking";
        state.error = "";
      })
      .addCase(sendChat.fulfilled, (state, action) => {
        state.status = "saved";
        state.lastResult = action.payload.tool_output;
        state.chat.push({
          role: "assistant",
          text: `${action.payload.answer} I updated the form on the left from your message.`,
        });
      })
      .addCase(sendChat.rejected, (state, action) => {
        state.status = "error";
        state.error = action.error.message;
      })
      .addCase(runToolsDemo.fulfilled, (state, action) => {
        state.demoResult = action.payload;
      });
  },
});

export const { setMode, setSelectedHcpId, appendUserMessage } = crmSlice.actions;

export const store = configureStore({
  reducer: {
    crm: crmSlice.reducer,
  },
});
