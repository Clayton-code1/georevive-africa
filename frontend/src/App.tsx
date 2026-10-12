import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Loading } from "./components/ui";
import { AuditLog } from "./pages/AuditLog";
import { Claims } from "./pages/Claims";
import { DataRoom } from "./pages/DataRoom";
import { DataSources } from "./pages/DataSources";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { MapExplorer } from "./pages/MapExplorer";
import { Prospectivity } from "./pages/Prospectivity";
import { Rescue } from "./pages/Rescue";
import { RescuePage } from "./pages/RescuePage";
import { ReviewQueue } from "./pages/ReviewQueue";
import type { ReactElement } from "react";
import { PresenterProvider } from "./presenter/Presenter";
import { HowTo } from "./pages/HowTo";

function Guard({ permission, children }: { permission?: string; children: ReactElement }) {
  const { can } = useAuth();
  if (permission && !can(permission)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <Loading label="Starting GeoRevive…" />;
  if (!user) return <Login />;
  return (
    <PresenterProvider>
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/sources" element={<Guard permission="sources.view"><DataSources /></Guard>} />
        <Route path="/rescue" element={<Guard permission="rescue.view"><Rescue /></Guard>} />
        <Route path="/rescue/:docId" element={<Guard permission="rescue.view"><RescuePage /></Guard>} />
        <Route path="/review" element={<Guard permission="facts.review"><ReviewQueue /></Guard>} />
        <Route path="/map" element={<Guard permission="map.view"><MapExplorer /></Guard>} />
        <Route path="/prospectivity" element={<Guard permission="model.view"><Prospectivity /></Guard>} />
        <Route path="/claims" element={<Guard permission="claims.create"><Claims /></Guard>} />
        <Route path="/dataroom" element={<Guard permission="dataroom.view"><DataRoom /></Guard>} />
        <Route path="/audit" element={<Guard permission="audit.view"><AuditLog /></Guard>} />
        <Route path="/help" element={<HowTo />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
    </PresenterProvider>
  );
}
