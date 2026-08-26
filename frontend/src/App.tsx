import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Overview from './pages/Overview';
import Control from './pages/Control';
import Tenders from './pages/Tenders';
import Partners from './pages/Partners';
import Events from './pages/Events';
import Saved from './pages/Saved';
import Assist from './pages/Assist';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/control" element={<Control />} />
        <Route path="/tenders" element={<Tenders />} />
        <Route path="/partners" element={<Partners />} />
        <Route path="/events" element={<Events />} />
        <Route path="/saved" element={<Saved />} />
        <Route path="/assist" element={<Assist />} />
        <Route path="*" element={<div className="state">Page introuvable.</div>} />
      </Route>
    </Routes>
  );
}
