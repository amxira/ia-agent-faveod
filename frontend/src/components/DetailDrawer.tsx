import type { ReactNode } from 'react';
import Icon from './Icon';

interface DetailDrawerProps {
  title: ReactNode;
  subtitle?: ReactNode;
  onClose: () => void;
  children: ReactNode;
}

export default function DetailDrawer({ title, subtitle, onClose, children }: DetailDrawerProps) {
  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Détail">
        <header>
          <div>
            <h3>{title}</h3>
            {subtitle && (
              <div className="muted" style={{ fontSize: 13, marginTop: 3 }}>
                {subtitle}
              </div>
            )}
          </div>
          <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Fermer">
            <Icon name="x" size={18} />
          </button>
        </header>
        <div className="body">{children}</div>
      </aside>
    </>
  );
}
