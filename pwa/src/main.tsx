import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import TasksPage from "./pages/TasksPage";
import CheckInPage from "./pages/CheckInPage";
import HistoryPage from "./pages/HistoryPage";
import ReflectionPage from "./pages/ReflectionPage";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/checkin/today" element={<CheckInPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/reflect/:checkinId" element={<ReflectionPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
