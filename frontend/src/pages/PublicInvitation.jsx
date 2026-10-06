import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { API, api } from "@/lib/api";
import { InvitationCard } from "@/features/InvitationCard";
import { Logo } from "@/components/wv/Logo";
import { PageLoader } from "@/components/wv/bits";

export default function PublicInvitation() {
  const { token } = useParams();
  const [inv, setInv] = useState(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    api.get(`/public/invitations/${token}`).then((r) => setInv(r.data)).catch(() => setMissing(true));
  }, [token]);

  if (missing) return <div className="flex min-h-screen items-center justify-center text-zinc-400" data-testid="public-invitation-missing">Deze uitnodiging bestaat niet (meer).</div>;
  if (!inv) return <PageLoader />;
  const photo = inv.photo_file_id ? `${API}/public/invitations/${token}/photo` : inv.photo_url;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#09090B] px-4 py-12" data-testid="public-invitation">
      <div className="wv-rise w-full max-w-md shadow-[0_40px_120px_-20px_rgba(0,0,0,0.9)]">
        <InvitationCard inv={inv} photo={photo} />
      </div>
      <div className="mt-10 opacity-60"><Logo /></div>
    </div>
  );
}
