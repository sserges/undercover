import { Link, NavLink, Route, Routes } from "react-router";
import { QueuePage } from "./QueuePage";

export function App() {
  return (
    <>
      <header className="header">
        <Link to="/" className="brand">
          <span className="brand-name">UnderCover</span>
          <span className="brand-tagline">Claims desk</span>
        </Link>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>
            Queue
          </NavLink>
          <NavLink to="/instructions">Instructions</NavLink>
        </nav>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<QueuePage />} />
          <Route path="*" element={<p className="panel">Page not found.</p>} />
        </Routes>
      </main>
    </>
  );
}
