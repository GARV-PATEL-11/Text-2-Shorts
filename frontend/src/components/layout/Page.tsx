// Page structure: every page is a Page (one width, one gutter), opening with a PageHeader; sections inside open with a
// SectionHeader. document.title follows the page.
import { type ReactNode, useEffect } from "react";

export function Page({ title, children, width = "wide" }: { title: string; children: ReactNode; width?: "wide" | "form" }) {
  useEffect(() => {
    document.title = `${title} · Faraday`;
  }, [title]);
  return <div className={`page page--${width}`}>{children}</div>;
}

export function PageHeader({ title, lead, actions, display }: { title: string; lead?: ReactNode; actions?: ReactNode; display?: boolean }) {
  return (
    <header className="page-header">
      <div className="page-header__text">
        <h1 className={display ? "page-header__title page-header__title--display" : "page-header__title"}>{title}</h1>
        {lead ? <p className="page-header__lead">{lead}</p> : null}
      </div>
      {actions ? <div className="page-header__actions">{actions}</div> : null}
    </header>
  );
}

export function Section({ title, description, actions, children }: { title: string; description?: ReactNode; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="section">
      <SectionHeader title={title} description={description} actions={actions} />
      {children}
    </section>
  );
}

export function SectionHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="section-header">
      <div>
        <h2 className="section-header__title">{title}</h2>
        {description ? <p className="section-header__description">{description}</p> : null}
      </div>
      {actions ? <div className="section-header__actions">{actions}</div> : null}
    </div>
  );
}
