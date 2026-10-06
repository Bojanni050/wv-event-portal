export const Logo = ({ subtitle, className = "" }) => (
  <div className={`flex items-center gap-3 ${className}`} data-testid="wv-logo">
    <div className="relative h-8 w-8 shrink-0">
      <span className="absolute inset-0 rotate-45 border border-[#D4AF37]/70" />
      <span className="absolute inset-[9px] rotate-45 bg-[#D4AF37]" />
    </div>
    <div className="leading-none">
      <p className="text-[13px] font-semibold tracking-[0.42em] text-white">WHITE VISION</p>
      {subtitle && <p className="mt-1 text-[10px] uppercase tracking-[0.3em] text-zinc-500">{subtitle}</p>}
    </div>
  </div>
);
