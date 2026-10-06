import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/wv/bits";
import CustomerLayout from "@/components/wv/CustomerLayout";
import AdminLayout from "@/components/wv/AdminLayout";
import Login from "@/pages/Login";
import Account from "@/pages/Account";
import RoleHome from "@/pages/RoleHome";
import EventOverview from "@/pages/EventOverview";
import PublicInvitation from "@/pages/PublicInvitation";
import EventDetails from "@/features/EventDetails";
import Chat from "@/features/Chat";
import Music from "@/features/Music";
import Timeline from "@/features/Timeline";
import InvitationBuilder from "@/features/InvitationBuilder";
import Files from "@/features/Files";
import GuestList from "@/features/GuestList";
import AdminDashboard from "@/pages/admin/AdminDashboard";
import AdminEvents from "@/pages/admin/AdminEvents";
import AdminEventDetail from "@/pages/admin/AdminEventDetail";
import AdminPeople from "@/pages/admin/AdminPeople";
import AdminTemplates from "@/pages/admin/AdminTemplates";

const STAFF = ["admin", "dj"];

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/u/:token" element={<PublicInvitation />} />
            <Route path="/" element={<ProtectedRoute><RoleHome /></ProtectedRoute>} />
            <Route path="/event/:eventId" element={<ProtectedRoute roles={["customer"]}><CustomerLayout /></ProtectedRoute>}>
              <Route index element={<EventOverview />} />
              <Route path="details" element={<EventDetails />} />
              <Route path="chat" element={<Chat />} />
              <Route path="muziek" element={<Music />} />
              <Route path="draaischema" element={<Timeline />} />
              <Route path="uitnodiging" element={<InvitationBuilder />} />
              <Route path="gasten" element={<GuestList />} />
              <Route path="bestanden" element={<Files />} />
              <Route path="account" element={<Account />} />
            </Route>
            <Route path="/admin" element={<ProtectedRoute roles={STAFF}><AdminLayout /></ProtectedRoute>}>
              <Route index element={<AdminDashboard />} />
              <Route path="events" element={<AdminEvents />} />
              <Route path="events/:eventId" element={<AdminEventDetail />} />
              <Route path="klanten" element={<AdminPeople kind="customers" />} />
              <Route path="djs" element={<AdminPeople kind="djs" />} />
              <Route path="sjablonen" element={<AdminTemplates />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster theme="dark" position="top-center" />
      </AuthProvider>
    </div>
  );
}

export default App;
