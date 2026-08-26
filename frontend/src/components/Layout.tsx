import { NavLink, Outlet } from 'react-router-dom';
import { useHealth } from '../hooks';
import Icon from './Icon';
import type { IconName } from './Icon';

const LINKS = [
  { to: '/', label: 'Vue d’ensemble', icon: 'house' as IconName, end: true },
  { to: '/control', label: 'Contrôle', icon: 'gauge' as IconName },
  { to: '/tenders', label: 'Tender Feed', icon: 'file' as IconName },
  { to: '/partners', label: 'Partenaires', icon: 'users' as IconName },
  { to: '/events', label: 'Événements & Leads', icon: 'calendar' as IconName },
  { to: '/saved', label: 'Favoris', icon: 'bookmark' as IconName },
  { to: '/assist', label: 'Assist', icon: 'chat' as IconName },
];

export default function Layout() {
  const { data, isError } = useHealth();

  return (
    <div className="shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <span className="brand-mark">
            <Icon name="pulse" size={20} />
          </span>
          <span className="brand-name">
            Faveod Intelligence
            <small>Agents IA · Veille B2B</small>
          </span>
        </NavLink>

        <nav className="navlist" aria-label="Navigation principale">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
            >
              <Icon name={l.icon} size={18} />
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <a href="/docs" target="_blank" rel="noreferrer">
            <Icon name="book" size={17} />
            API Docs (Swagger)
          </a>
          <div className="health-pill">
            <span className={`dot ${isError ? 'down' : data ? 'ok' : ''}`} />
            {isError ? 'API hors ligne' : data ? 'API en ligne' : 'Connexion…'}
          </div>
        </div>
      </aside>

      <main className="content">
        <div className="page">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
