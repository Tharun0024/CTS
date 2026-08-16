import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Building2, ShieldCheck, ArrowRight,
  Activity, ArrowUpRight,
  Hexagon, Triangle, Command, Ghost, HeartPulse, Zap, CheckSquare,
  Check, Terminal, FileText, BrainCircuit, CheckCircle2, FileCheck,
  Workflow, ShieldAlert, ChevronDown, Sparkles
} from 'lucide-react';
import { useRole } from '../context/RoleContext';

/* ─── tiny hook: animate on viewport entry ─── */
function useFadeIn(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

const Fade = ({ children, delay = 0, className = '' }: { children: React.ReactNode; delay?: number; className?: string }) => {
  const { ref, visible } = useFadeIn();
  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(28px)',
        transition: `opacity 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) ${delay}ms, transform 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
};

/* ─── Animated Number Counter ─── */
const AnimatedCounter = ({ end, suffix = '', duration = 2000 }: { end: number, suffix?: string, duration?: number }) => {
  const { ref, visible } = useFadeIn();
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!visible) return;
    let startTimestamp: number;
    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // easeOutExpo
      const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setCount(Math.floor(easeProgress * end));
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  }, [visible, end, duration]);

  return <span ref={ref}>{count}{suffix}</span>;
};

/* ─── Spotlight Hover Card ─── */
const SpotlightCard = ({ children, className = '', onClick, style = {} }: any) => {
  const divRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [opacity, setOpacity] = useState(0);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!divRef.current) return;
    const rect = divRef.current.getBoundingClientRect();
    setPosition({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  return (
    <div
      ref={divRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setOpacity(1)}
      onMouseLeave={() => setOpacity(0)}
      onClick={onClick}
      className={className}
      style={{ position: 'relative', overflow: 'hidden', ...style }}
    >
      <div
        style={{
          position: 'absolute', inset: '-1px', pointerEvents: 'none',
          opacity, transition: 'opacity 0.3s ease',
          background: `radial-gradient(400px circle at ${position.x}px ${position.y}px, rgba(255,255,255,0.08), transparent 40%)`,
          zIndex: 1,
        }}
      />
      <div style={{ position: 'relative', zIndex: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
        {children}
      </div>
    </div>
  );
};



/* ─── FAQ Data ─── */
const FAQS = [
  {
    q: "Is patient data secure and HIPAA compliant?",
    a: "Absolutely. ORCA PolicyAI employs end-to-end encryption (AES-256) at rest and in transit. Our infrastructure is fully HIPAA compliant and undergoes annual SOC 2 Type II audits. Patient PII/PHI is never used to train foundation models."
  },
  {
    q: "How long does it take to integrate with existing EHR systems?",
    a: "Our standard API and HL7/FHIR connectors typically allow for complete integration within 2-4 weeks. We support major EHRs including Epic, Cerner, and Meditech out of the box."
  },
  {
    q: "What happens if the AI is unsure about a claim?",
    a: "If confidence scores fall below a custom-defined threshold (e.g., 95%), the claim is automatically routed to the Human Review Queue in the Insurance Portal, complete with highlighted evidence and missing criteria notes."
  },
  {
    q: "Can hospitals use this without the insurer being on the platform?",
    a: "Yes. Hospitals can use the pre-submission AI check to validate claims against known payer rules before sending them via traditional clearinghouses, drastically reducing denial rates."
  }
];

export function RoleSelect() {
  const navigate = useNavigate();
  const { setRole } = useRole();
  const [scrolled, setScrolled] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const [showSignIn, setShowSignIn] = useState(false);
  const [authMode, setAuthMode] = useState<'signin' | 'signup'>('signin');
  const [authStep, setAuthStep] = useState<'credentials' | 'portal'>('credentials');
  const [selectedTarget, setSelectedTarget] = useState<'hospital' | 'insurance' | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 30);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const openAuth = (target?: 'hospital' | 'insurance') => {
    setShowSignIn(true);
    setAuthStep('credentials');
    setAuthMode('signin');
    setSelectedTarget(target || null);
    setErrorMsg('');
  };

  const handleContinue = () => {
    setErrorMsg('');
    const defaultUsers = [
      { name: 'Dr. S. Jenkins', email: 'user@example.com' },
      { name: 'Alex Reynolds', email: 'alex.r@aetna.com' }
    ];
    let registeredUsers = JSON.parse(localStorage.getItem('orca_registered_users') || '[]');
    if (registeredUsers.length === 0) {
      registeredUsers = defaultUsers;
      localStorage.setItem('orca_registered_users', JSON.stringify(registeredUsers));
    }

    if (authMode === 'signup') {
      if (!username.trim()) {
        setErrorMsg('Username is required');
        return;
      }
      if (password !== confirmPassword) {
        setErrorMsg('Passwords do not match');
        return;
      }
      const existingIdx = registeredUsers.findIndex((u: any) => u.email.toLowerCase() === email.toLowerCase());
      const newUser = { name: username.trim(), email: email.trim().toLowerCase() };
      if (existingIdx !== -1) {
        registeredUsers[existingIdx] = newUser;
      } else {
        registeredUsers.push(newUser);
      }
      localStorage.setItem('orca_registered_users', JSON.stringify(registeredUsers));
      localStorage.setItem('orca_logged_user', JSON.stringify(newUser));
    } else {
      const matchedUser = registeredUsers.find((u: any) => u.email.toLowerCase() === email.toLowerCase());
      if (matchedUser) {
        localStorage.setItem('orca_logged_user', JSON.stringify(matchedUser));
      } else {
        const namePart = email.split('@')[0];
        const formattedName = namePart.split(/[\._-]/).map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
        const newUser = { name: formattedName || 'Guest User', email: email.trim().toLowerCase() };
        registeredUsers.push(newUser);
        localStorage.setItem('orca_registered_users', JSON.stringify(registeredUsers));
        localStorage.setItem('orca_logged_user', JSON.stringify(newUser));
      }
    }

    if (selectedTarget) {
      selectPortal(selectedTarget);
    } else {
      setAuthStep('portal');
    }
  };

  const selectPortal = (role: 'hospital' | 'insurance') => {
    setRole(role);
    navigate(`/${role}/dashboard`);
  };

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen font-sans overflow-x-hidden" style={{ background: '#030712', color: '#f8fafc' }}>

      {/* ─── GLOBAL STYLE INJECTION ─── */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body { font-family: 'Inter', sans-serif; }

        @keyframes gridMove {
          0% { background-position: 0 0; }
          100% { background-position: 40px 40px; }
        }
        @keyframes glow-pulse {
          0%, 100% { opacity: 0.5; transform: scale(1); }
          50% { opacity: 0.8; transform: scale(1.08); }
        }
        @keyframes breathe {
          0%, 100% { transform: scale(1) translate(0, 0); opacity: 0.4; filter: hue-rotate(0deg); }
          50% { transform: scale(1.1) translate(10px, -10px); opacity: 0.6; filter: hue-rotate(15deg); }
        }
        @keyframes marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        @keyframes beam {
          0% { left: -60%; }
          100% { left: 110%; }
        }
        @keyframes float-y {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
        @keyframes cursor-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }

        .marquee-track { 
          display: flex;
          width: fit-content;
          animation: marquee 30s linear infinite; 
        }
        .marquee-track:hover { animation-play-state: paused; }

        .breathe-emerald { animation: breathe 8s ease-in-out infinite; }
        .breathe-blue { animation: breathe 9s ease-in-out infinite 1s; }

        .float-icon { animation: float-y 4s ease-in-out infinite; }
        .float-icon-delayed { animation: float-y 4.5s ease-in-out infinite 1s; }

        .beam-shine::after {
          content: '';
          position: absolute;
          top: 0; bottom: 0; width: 60%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
          animation: beam 3s ease-in-out infinite;
        }

        .portal-card {
          transition: transform 0.35s cubic-bezier(.22,.68,0,1.2), box-shadow 0.35s ease, border-color 0.25s ease;
        }
        .portal-card:hover { transform: translateY(-8px) scale(1.01); }
        .portal-card:active { transform: translateY(-2px) scale(0.99); }

        .nav-link {
          position: relative;
          color: #94a3b8;
          font-size: 14px;
          font-weight: 500;
          transition: color 0.2s;
          padding: 4px 0;
          cursor: pointer;
          border: none;
          background: none;
        }
        .nav-link::after {
          content: '';
          position: absolute;
          bottom: -2px; left: 0;
          width: 0; height: 2px;
          background: linear-gradient(90deg, #3b82f6, #10b981);
          transition: width 0.3s ease;
          border-radius: 2px;
        }
        .nav-link:hover { color: #f8fafc; }
        .nav-link:hover::after { width: 100%; }

        .step-dot {
          width: 10px; height: 10px;
          border-radius: 50%;
          transition: all 0.4s ease;
          cursor: pointer;
          border: none;
        }

        .gradient-text {
          background: linear-gradient(135deg, #ffffff 0%, #94a3b8 40%, #3b82f6 70%, #10b981 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .hero-gradient-text {
          background: linear-gradient(135deg, #ffffff 0%, #e2e8f0 30%, #60a5fa 60%, #34d399 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .divider-glow {
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(59,130,246,0.3) 30%, rgba(16,185,129,0.3) 70%, transparent);
        }
          
        .terminal-text {
          font-family: 'Fira Code', monospace;
        }
        .terminal-cursor {
          display: inline-block;
          width: 8px;
          height: 16px;
          background: #34d399;
          vertical-align: middle;
          margin-left: 4px;
          animation: cursor-blink 1s step-end infinite;
        }

        .faq-button {
          transition: background 0.2s;
        }
        .faq-button:hover {
          background: rgba(255,255,255,0.03);
        }
      `}</style>

      {/* ─── AMBIENT CANVAS ─── */}
      <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
        <div style={{
          position: 'absolute', inset: 0,
          backgroundImage: `
            linear-gradient(rgba(59,130,246,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59,130,246,0.04) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px',
          animation: 'gridMove 8s linear infinite',
        }} />
        <CheckSquare width={32 as any} className="text-emerald-500 opacity-20 hover:opacity-100 hover:scale-110 transition-all duration-300" />
        <div className="breathe-emerald" style={{ position: 'absolute', top: '-120px', left: '15%', width: '700px', height: '700px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(16,185,129,0.12) 0%, transparent 70%)', filter: 'blur(40px)' }} />
        <div className="breathe-blue" style={{ position: 'absolute', top: '-80px', right: '10%', width: '600px', height: '600px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%)', filter: 'blur(40px)' }} />
      </div>

      {/* ─── NAVBAR ─── */}
      <header style={{
        position: 'sticky', top: 0, zIndex: 100,
        borderBottom: scrolled ? '1px solid rgba(255,255,255,0.08)' : '1px solid transparent',
        backdropFilter: scrolled ? 'blur(24px) saturate(180%)' : 'blur(0px)',
        background: scrolled ? 'rgba(3,7,18,0.85)' : 'transparent',
        transition: 'all 0.4s ease',
      }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '0 24px', height: '72px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }} onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div style={{ width: '38px', height: '38px', borderRadius: '12px', background: 'linear-gradient(135deg, #3b82f6, #10b981)', padding: '1.5px', boxShadow: '0 0 20px rgba(59,130,246,0.3)' }}>
              <div style={{ width: '100%', height: '100%', borderRadius: '10px', background: '#030712', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Activity size={18} color="#60a5fa" />
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontFamily: 'Inter', fontWeight: 800, fontSize: '20px', letterSpacing: '-0.5px', color: '#f8fafc' }}>ORCA</span>
              <span style={{ fontSize: '10px', fontWeight: 600, letterSpacing: '0.1em', padding: '2px 8px', borderRadius: '20px', background: 'rgba(59,130,246,0.12)', color: '#60a5fa', border: '1px solid rgba(59,130,246,0.25)' }}>POLICYAI</span>
            </div>
          </div>

          <nav style={{ display: 'flex', gap: '40px', alignItems: 'center' }} className="hidden-mobile">
            <button className="nav-link" onClick={() => scrollTo('portals')}>Platform</button>
            <button className="nav-link" onClick={() => scrollTo('engine')}>AI Engine</button>
            <button className="nav-link" onClick={() => scrollTo('security')}>Security</button>
            <button className="nav-link" onClick={() => scrollTo('faq')}>FAQ</button>
          </nav>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button className="nav-link" onClick={() => openAuth()} style={{ display: window.innerWidth < 640 ? 'none' : undefined }}>
              Sign In
            </button>
            <button
              onClick={() => openAuth()}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '10px 20px', borderRadius: '12px',
                background: 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(16,185,129,0.15))',
                border: '1px solid rgba(59,130,246,0.3)',
                color: '#f8fafc', fontWeight: 600, fontSize: '14px',
                cursor: 'pointer', transition: 'all 0.2s',
                backdropFilter: 'blur(10px)',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'linear-gradient(135deg, rgba(59,130,246,0.25), rgba(16,185,129,0.25))'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(59,130,246,0.5)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(16,185,129,0.15))'; (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(59,130,246,0.3)'; }}
            >
              Enter Workspace <ArrowUpRight size={14} />
            </button>
          </div>
        </div>
      </header>

      <main style={{ position: 'relative', zIndex: 10 }}>

        {/* ═══════════════════════════════════════════════
            SECTION 1 — HERO
        ═══════════════════════════════════════════════ */}
        <section style={{ padding: '100px 24px 80px', maxWidth: '1280px', margin: '0 auto', textAlign: 'center' }}>
          <Fade delay={0}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', padding: '8px 18px', borderRadius: '100px', background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', marginBottom: '32px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 10px #10b981', animation: 'glow-pulse 2s ease-in-out infinite', display: 'inline-block' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, letterSpacing: '0.12em', color: '#34d399', textTransform: 'uppercase' }}>
                Enterprise Claims Automation
              </span>
            </div>
          </Fade>

          <Fade delay={80}>
            <h1 style={{ fontSize: 'clamp(48px, 7vw, 92px)', fontWeight: 900, lineHeight: 1.05, letterSpacing: '-0.04em', marginBottom: '28px' }}>
              <span style={{ color: '#f8fafc' }}>Prior Authorizations,</span><br />
              <span className="hero-gradient-text">Simplified With AI</span>
            </h1>
          </Fade>

          <Fade delay={160}>
            <p style={{ fontSize: '18px', fontWeight: 400, color: '#64748b', lineHeight: 1.75, maxWidth: '640px', margin: '0 auto 48px' }}>
              Connect hospitals and insurers through intelligent claim verification, real-time policy analysis, and automated prior authorization workflows.
            </p>
          </Fade>

          <Fade delay={240}>
            <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '64px' }}>
              <button
                onClick={() => scrollTo('portals')}
                style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '16px 32px', borderRadius: '14px',
                  background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                  border: 'none', color: '#fff', fontWeight: 700, fontSize: '15px',
                  cursor: 'pointer', boxShadow: '0 0 30px rgba(59,130,246,0.35), 0 8px 24px rgba(59,130,246,0.2)',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)'; (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 0 40px rgba(59,130,246,0.45), 0 12px 32px rgba(59,130,246,0.3)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)'; (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 0 30px rgba(59,130,246,0.35), 0 8px 24px rgba(59,130,246,0.2)'; }}
              >
                Explore Portals <ArrowRight size={16} />
              </button>
            </div>
          </Fade>
        </section>

        {/* ═══════════════════════════════════════════════
            SECTION 1.5 — TRUST & METRICS (NEW)
        ═══════════════════════════════════════════════ */}
        <section style={{ padding: '0 24px 100px', maxWidth: '1280px', margin: '0 auto' }}>
          <Fade delay={400}>
            <div style={{ textAlign: 'center', marginBottom: '40px' }}>
              <p style={{ fontSize: '12px', fontWeight: 600, letterSpacing: '0.15em', color: '#475569', textTransform: 'uppercase' }}>
                Trusted by leading healthcare networks and payers
              </p>
            </div>

            {/* Simulated Logo Marquee */}
            <div style={{ overflow: 'hidden', position: 'relative', width: '100%', maskImage: 'linear-gradient(to right, transparent, black 10%, black 90%, transparent)' }}>
              <div className="marquee-track" style={{ gap: '64px', paddingRight: '64px' }}>
                {[...Array(2)].map((_, i) => (
                  <React.Fragment key={i}>
                    {[
                      { icon: Hexagon, name: 'Apex Health' },
                      { icon: Triangle, name: 'Quantum Care' },
                      { icon: Command, name: 'BlueCross Group' },
                      { icon: Ghost, name: 'Phantom Med' },
                      { icon: HeartPulse, name: 'Vitality Partners' },
                      { icon: Zap, name: 'Nexus Insurance' }
                    ].map((Brand, j) => (
                      <div key={j} style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#475569' }}>
                        <Brand.icon size={24} />
                        <span style={{ fontSize: '16px', fontWeight: 700, letterSpacing: '-0.02em' }}>{Brand.name}</span>
                      </div>
                    ))}
                  </React.Fragment>
                ))}
              </div>
            </div>

            {/* Key Metrics Strip with Animated Counters */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px', marginTop: '64px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '40px' }}>
              {[
                { prefix: '$', end: 2.4, suffix: 'B+', desc: 'Claims processed annually', float: true },
                { prefix: '', end: 85, suffix: '%', desc: 'Reduction in manual review' },
                { prefix: '', end: 99, suffix: '.8%', desc: 'AI entity extraction accuracy' },
                { text: 'SOC 2', desc: 'Type II & HIPAA Compliant' }
              ].map((m, i) => (
                <div key={i} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '32px', fontWeight: 900, color: '#f8fafc', letterSpacing: '-0.03em', marginBottom: '8px' }}>
                    {m.text ? m.text : (
                      <>
                        {m.prefix}
                        <AnimatedCounter end={m.end || 0} />
                        {m.suffix}
                      </>
                    )}
                  </div>
                  <div style={{ fontSize: '13px', color: '#64748b' }}>{m.desc}</div>
                </div>
              ))}
            </div>
          </Fade>
        </section>

        {/* ═══════════════════════════════════════════════
            SECTION 2 — PORTAL SELECTION (Primary CTA)
        ═══════════════════════════════════════════════ */}
        <section id="portals" style={{ padding: '60px 24px 100px', maxWidth: '1280px', margin: '0 auto' }}>
          <Fade>
            <div style={{ textAlign: 'center', marginBottom: '64px' }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '5px 16px', borderRadius: '100px', background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', marginBottom: '20px' }}>
                <span style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.14em', color: '#60a5fa', textTransform: 'uppercase' }}>Workspace Access</span>
              </div>
              <h2 style={{ fontSize: 'clamp(32px, 4vw, 56px)', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '16px', color: '#f8fafc' }}>
                Choose Your Portal
              </h2>
              <p style={{ fontSize: '16px', color: '#64748b', maxWidth: '480px', margin: '0 auto', lineHeight: 1.7 }}>
                Two distinct workspaces. One unified authorization platform.
              </p>
            </div>
          </Fade>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', maxWidth: '900px', margin: '0 auto' }}>
            {/* Hospital Card with Spotlight Effect */}
            <Fade delay={80}>
              <SpotlightCard
                className="portal-card beam-shine"
                onClick={() => openAuth('hospital')}
                style={{
                  cursor: 'pointer', borderRadius: '24px', padding: '40px',
                  border: '1px solid rgba(16,185,129,0.2)',
                  background: 'linear-gradient(160deg, rgba(16,185,129,0.06) 0%, rgba(3,7,18,0.9) 60%)',
                  backdropFilter: 'blur(16px)',
                  boxShadow: '0 0 0 1px rgba(255,255,255,0.04) inset, 0 32px 64px rgba(0,0,0,0.4)',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', height: '100%' }}>
                  <div style={{ width: '64px', height: '64px', borderRadius: '18px', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 20px rgba(16,185,129,0.15)' }}>
                    <Building2 size={28} color="#34d399" />
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.14em', color: '#10b981', textTransform: 'uppercase', marginBottom: '10px' }}>Hospital Workspace</div>
                    <h3 style={{ fontSize: '26px', fontWeight: 800, letterSpacing: '-0.02em', color: '#f1f5f9', marginBottom: '12px' }}>Hospital Portal</h3>
                    <p style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.75 }}>
                      Submit claims, upload supporting documents, track approvals in real-time, and manage resubmissions from one unified workspace.
                    </p>
                  </div>
                  <ul style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {['Submit claims', 'Upload documents', 'Track claim status', 'AI-assisted resubmission'].map((f, i) => (
                      <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', color: '#cbd5e1', fontWeight: 500 }}>
                        <div style={{ width: '18px', height: '18px', borderRadius: '50%', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <Check size={10} color="#34d399" />
                        </div>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={e => { e.stopPropagation(); openAuth('hospital'); }}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                      padding: '16px 24px', borderRadius: '14px',
                      background: 'linear-gradient(135deg, #059669, #10b981)',
                      border: 'none', color: '#fff', fontWeight: 700, fontSize: '14px',
                      cursor: 'pointer', boxShadow: '0 4px 20px rgba(16,185,129,0.3)',
                      transition: 'all 0.2s', marginTop: 'auto',
                    }}
                  >
                    Enter Hospital Portal <ArrowRight size={16} />
                  </button>
                </div>
              </SpotlightCard>
            </Fade>

            {/* Insurance Card with Spotlight Effect */}
            <Fade delay={160}>
              <SpotlightCard
                className="portal-card beam-shine"
                onClick={() => openAuth('insurance')}
                style={{
                  cursor: 'pointer', borderRadius: '24px', padding: '40px',
                  border: '1px solid rgba(59,130,246,0.2)',
                  background: 'linear-gradient(160deg, rgba(59,130,246,0.06) 0%, rgba(3,7,18,0.9) 60%)',
                  backdropFilter: 'blur(16px)',
                  boxShadow: '0 0 0 1px rgba(255,255,255,0.04) inset, 0 32px 64px rgba(0,0,0,0.4)',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', height: '100%' }}>
                  <div style={{ width: '64px', height: '64px', borderRadius: '18px', background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 20px rgba(59,130,246,0.15)' }}>
                    <ShieldCheck size={28} color="#60a5fa" />
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.14em', color: '#3b82f6', textTransform: 'uppercase', marginBottom: '10px' }}>Insurance Workspace</div>
                    <h3 style={{ fontSize: '26px', fontWeight: 800, letterSpacing: '-0.02em', color: '#f1f5f9', marginBottom: '12px' }}>Insurance Portal</h3>
                    <p style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.75 }}>
                      Review incoming claims, analyze policy evidence with AI, render decisions, and manage the human review queue efficiently.
                    </p>
                  </div>
                  <ul style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {['Incoming claims queue', 'AI policy analysis', 'Claim decision workflow', 'Human review queue'].map((f, i) => (
                      <li key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px', color: '#cbd5e1', fontWeight: 500 }}>
                        <div style={{ width: '18px', height: '18px', borderRadius: '50%', background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <Check size={10} color="#60a5fa" />
                        </div>
                        {f}
                      </li>
                    ))}
                  </ul>
                  <button
                    onClick={e => { e.stopPropagation(); openAuth('insurance'); }}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                      padding: '16px 24px', borderRadius: '14px',
                      background: 'linear-gradient(135deg, #1d4ed8, #3b82f6)',
                      border: 'none', color: '#fff', fontWeight: 700, fontSize: '14px',
                      cursor: 'pointer', boxShadow: '0 4px 20px rgba(59,130,246,0.3)',
                      transition: 'all 0.2s', marginTop: 'auto',
                    }}
                  >
                    Enter Insurance Portal <ArrowRight size={16} />
                  </button>
                </div>
              </SpotlightCard>
            </Fade>
          </div>
        </section>

        {/* ═══════════════════════════════════════════════
            SECTION 3 — AI ENGINE VERIFICATION (NEW)
        ═══════════════════════════════════════════════ */}
        <section id="engine" style={{ padding: '100px 24px', maxWidth: '1280px', margin: '0 auto' }}>
          <div className="divider-glow" style={{ marginBottom: '80px' }} />

          <div style={{ display: 'flex', flexDirection: window.innerWidth < 900 ? 'column' : 'row', gap: '64px', alignItems: 'center' }}>
            <div style={{ flex: 1 }}>
              <Fade>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '5px 16px', borderRadius: '100px', background: 'rgba(236,72,153,0.08)', border: '1px solid rgba(236,72,153,0.2)', marginBottom: '20px' }}>
                  <span style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.14em', color: '#f472b6', textTransform: 'uppercase' }}>Proprietary AI Engine</span>
                </div>
                <h2 style={{ fontSize: 'clamp(32px, 4vw, 48px)', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '24px', color: '#f8fafc', lineHeight: 1.1 }}>
                  Instant Evidence<br />Verification
                </h2>
                <p style={{ fontSize: '16px', color: '#64748b', lineHeight: 1.75, marginBottom: '32px' }}>
                  Our specialized LLM architecture ingests unstructured clinical notes, lab results, and imaging reports to automatically extract key medical entities.
                  It then cross-references this data against thousands of active insurer policies in milliseconds.
                </p>

                <ul style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {[
                    { title: 'Automated OCR', desc: 'Extract text from PDFs and scanned images instantly.' },
                    { title: 'Semantic Matching', desc: 'Maps local hospital codes to standard payer terminologies.' },
                    { title: 'Audit Trails', desc: 'Every AI decision is logged with direct citations to medical records.' }
                  ].map((item, i) => (
                    <li key={i} style={{ display: 'flex', gap: '16px' }}>
                      <div style={{ width: '24px', height: '24px', borderRadius: '6px', background: 'rgba(236,72,153,0.1)', border: '1px solid rgba(236,72,153,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '2px' }}>
                        <Check size={12} color="#f472b6" />
                      </div>
                      <div>
                        <div style={{ fontSize: '15px', fontWeight: 600, color: '#f1f5f9', marginBottom: '4px' }}>{item.title}</div>
                        <div style={{ fontSize: '14px', color: '#64748b' }}>{item.desc}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              </Fade>
            </div>

            {/* Simulated Terminal UI */}
            <div style={{ flex: 1, width: '100%' }}>
              <Fade delay={200}>
                <div style={{
                  borderRadius: '16px', border: '1px solid #1e293b', background: '#0f172a',
                  boxShadow: '0 24px 64px rgba(0,0,0,0.4)', overflow: 'hidden'
                }}>
                  {/* Terminal Header */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 16px', background: '#020617', borderBottom: '1px solid #1e293b' }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ef4444' }} />
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#f59e0b' }} />
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#10b981' }} />
                    <div style={{ marginLeft: '12px', fontSize: '12px', color: '#64748b', fontFamily: 'monospace', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Terminal size={12} /> parser.js — claim_auth
                    </div>
                  </div>
                  {/* Terminal Body */}
                  <div className="terminal-text" style={{ padding: '24px', fontSize: '13px', lineHeight: 1.6, color: '#cbd5e1' }}>
                    <div style={{ color: '#3b82f6' }}>$ <span style={{ color: '#e2e8f0' }}>orca-engine extract --file patient_notes.pdf</span></div>
                    <div style={{ color: '#64748b', marginTop: '8px' }}>[INFO] Initializing OCR model v4.2...</div>
                    <div style={{ color: '#64748b' }}>[INFO] Document parsed in 142ms. 3 entities found.</div>
                    <br />
                    <div><span style={{ color: '#c084fc' }}>const</span> evidence = {'{'}</div>
                    <div style={{ paddingLeft: '16px' }}>
                      <span style={{ color: '#f472b6' }}>"diagnosis"</span>: <span style={{ color: '#34d399' }}>"M54.5"</span>, <span style={{ color: '#64748b' }}>// Low back pain</span><br />
                      <span style={{ color: '#f472b6' }}>"duration_weeks"</span>: <span style={{ color: '#fbbf24' }}>12</span>,<br />
                      <span style={{ color: '#f472b6' }}>"prior_treatments"</span>: [<span style={{ color: '#34d399' }}>"physical_therapy"</span>, <span style={{ color: '#34d399' }}>"NSAIDs"</span>]<br />
                    </div>
                    <div>{'}'}</div>
                    <br />
                    <div style={{ color: '#3b82f6' }}>$ <span style={{ color: '#e2e8f0' }}>orca-engine evaluate --policy UHC_SPINE_01</span></div>
                    <div style={{ color: '#10b981', marginTop: '8px' }}>✔ Criteria matched: duration &gt; 6 weeks</div>
                    <div style={{ color: '#10b981' }}>✔ Criteria matched: failed conservative therapy</div>
                    <br />
                    <div><span style={{ color: '#60a5fa', fontWeight: 600 }}>[SUCCESS]</span> Authorization Recommended (Confidence: 99.4%)<span className="terminal-cursor"></span></div>
                  </div>
                </div>
              </Fade>
            </div>
          </div>
        </section>

        {/* ═══════════════════════════════════════════════
            SECTION 4 — HOW IT WORKS
        ═══════════════════════════════════════════════ */}
        <section id="how-it-works" style={{ padding: '100px 24px', maxWidth: '1280px', margin: '0 auto' }}>
          <div className="divider-glow" style={{ marginBottom: '80px' }} />

          <Fade>
            <div style={{ textAlign: 'center', marginBottom: '64px' }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '5px 16px', borderRadius: '100px', background: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)', marginBottom: '20px' }}>
                <span style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.14em', color: '#a78bfa', textTransform: 'uppercase' }}>Process Pipeline</span>
              </div>
              <h2 style={{ fontSize: 'clamp(28px, 3.5vw, 48px)', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '16px', color: '#f8fafc' }}>From Claim to Decision</h2>
              <p style={{ fontSize: '16px', color: '#64748b', maxWidth: '420px', margin: '0 auto', lineHeight: 1.7 }}>
                Three steps. One streamlined authorization flow.
              </p>
            </div>
          </Fade>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', maxWidth: '960px', margin: '0 auto' }}>
            {[
              { n: '01', title: 'Submit', desc: 'Hospitals submit claims and clinical documents through their secure workspace.', color: '#10b981', icon: FileText },
              { n: '02', title: 'Analyze', desc: 'AI extracts clinical entities and cross-checks against active policy requirements.', color: '#3b82f6', icon: BrainCircuit },
              { n: '03', title: 'Decide', desc: 'Insurance teams review AI findings and make faster, audit-ready decisions.', color: '#8b5cf6', icon: CheckCircle2 },
            ].map((step, i) => {
              const Icon = step.icon;
              return (
                <Fade key={i} delay={i * 100}>
                  <div style={{
                    padding: '36px', borderRadius: '20px',
                    border: '1px solid rgba(255,255,255,0.07)',
                    background: 'rgba(15,23,42,0.5)',
                    backdropFilter: 'blur(12px)',
                    position: 'relative', overflow: 'hidden',
                    transition: 'border-color 0.3s, transform 0.3s',
                  }}
                    onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = `${step.color}40`; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-4px)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.07)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'; }}
                  >
                    <div style={{ fontSize: '48px', fontWeight: 900, color: `${step.color}30`, fontFamily: 'monospace', letterSpacing: '-0.04em', lineHeight: 1, marginBottom: '20px' }}>{step.n}</div>
                    <div style={{ width: '40px', height: '40px', borderRadius: '12px', background: `${step.color}15`, border: `1px solid ${step.color}30`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px' }}>
                      <Icon size={20} color={step.color} className={i % 2 === 0 ? "float-icon" : "float-icon-delayed"} />
                    </div>
                    <h3 style={{ fontSize: '20px', fontWeight: 700, color: '#f1f5f9', marginBottom: '10px' }}>{step.title}</h3>
                    <p style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.75 }}>{step.desc}</p>
                  </div>
                </Fade>
              );
            })}
          </div>
        </section>

        {/* ═══════════════════════════════════════════════
            SECTION 5 — SECURITY & CAPABILITIES
        ═══════════════════════════════════════════════ */}
        <section id="security" style={{ padding: '100px 24px', maxWidth: '1280px', margin: '0 auto' }}>
          <div className="divider-glow" style={{ marginBottom: '80px' }} />

          <Fade>
            <div style={{ textAlign: 'center', marginBottom: '64px' }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '5px 16px', borderRadius: '100px', background: 'rgba(6,182,212,0.08)', border: '1px solid rgba(6,182,212,0.2)', marginBottom: '20px' }}>
                <span style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.14em', color: '#22d3ee', textTransform: 'uppercase' }}>Platform Capabilities</span>
              </div>
              <h2 style={{ fontSize: 'clamp(28px, 3.5vw, 48px)', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '16px', color: '#f8fafc' }}>Built for Real-World Claims</h2>
              <p style={{ fontSize: '16px', color: '#64748b', maxWidth: '460px', margin: '0 auto', lineHeight: 1.7 }}>
                Verified operational capabilities at the core of every authorization workflow.
              </p>
            </div>
          </Fade>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', maxWidth: '960px', margin: '0 auto' }}>
            {[
              { title: 'AI Document Analysis', desc: 'Automated OCR and clinical entity extraction from unstructured medical records.', icon: FileCheck, color: '#3b82f6' },
              { title: 'Policy Evidence Check', desc: 'Real-time cross-referencing against insurer policy criteria and clinical guidelines.', icon: BrainCircuit, color: '#10b981' },
              { title: 'Real-Time Tracking', desc: 'Live claim status from hospital submission through final payer resolution.', icon: Workflow, color: '#8b5cf6' },
              { title: 'Secure Role Isolation', desc: 'Strict portal separation ensuring hospital and insurance data partitions are protected.', icon: ShieldAlert, color: '#06b6d4' },
            ].map((cap, i) => {
              const Icon = cap.icon;
              return (
                <Fade key={i} delay={i * 80}>
                  <div style={{
                    padding: '28px', borderRadius: '18px',
                    border: '1px solid rgba(255,255,255,0.06)',
                    background: 'rgba(15,23,42,0.4)',
                    backdropFilter: 'blur(12px)',
                    transition: 'border-color 0.3s, transform 0.3s',
                  }}
                    onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = `${cap.color}35`; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-4px)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.06)'; (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)'; }}
                  >
                    <div style={{ width: '44px', height: '44px', borderRadius: '13px', background: `${cap.color}12`, border: `1px solid ${cap.color}25`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '18px', boxShadow: `0 0 16px ${cap.color}15` }}>
                      <Icon size={21} color={cap.color} className={i % 2 === 0 ? "float-icon" : "float-icon-delayed"} />
                    </div>
                    <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#f1f5f9', marginBottom: '8px' }}>{cap.title}</h4>
                    <p style={{ fontSize: '13px', color: '#64748b', lineHeight: 1.7 }}>{cap.desc}</p>
                  </div>
                </Fade>
              );
            })}
          </div>
        </section>

        {/* ═══════════════════════════════════════════════
            SECTION 6 — FAQ (NEW)
        ═══════════════════════════════════════════════ */}
        <section id="faq" style={{ padding: '100px 24px', maxWidth: '1280px', margin: '0 auto' }}>
          <div className="divider-glow" style={{ marginBottom: '80px' }} />

          <Fade>
            <div style={{ textAlign: 'center', marginBottom: '48px' }}>
              <h2 style={{ fontSize: 'clamp(28px, 3.5vw, 40px)', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '16px', color: '#f8fafc' }}>
                Frequently Asked Questions
              </h2>
            </div>
          </Fade>

          <div style={{ maxWidth: '720px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {FAQS.map((faq, i) => (
              <Fade key={i} delay={i * 50}>
                <div style={{ border: '1px solid rgba(255,255,255,0.08)', borderRadius: '16px', overflow: 'hidden', background: 'rgba(15,23,42,0.4)', backdropFilter: 'blur(12px)' }}>
                  <button
                    className="faq-button"
                    onClick={() => setOpenFaq(openFaq === i ? null : i)}
                    style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '24px', background: 'none', border: 'none', cursor: 'pointer', color: '#f1f5f9', textAlign: 'left' }}
                  >
                    <span style={{ fontSize: '16px', fontWeight: 600 }}>{faq.q}</span>
                    <ChevronDown size={20} style={{ color: '#64748b', transform: openFaq === i ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s' }} />
                  </button>
                  <div style={{
                    maxHeight: openFaq === i ? '200px' : '0px', opacity: openFaq === i ? 1 : 0,
                    transition: 'all 0.3s ease', overflow: 'hidden'
                  }}>
                    <p style={{ padding: '0 24px 24px', color: '#94a3b8', fontSize: '15px', lineHeight: 1.7 }}>
                      {faq.a}
                    </p>
                  </div>
                </div>
              </Fade>
            ))}
          </div>
        </section>

        {/* ═══════════════════════════════════════════════
            SECTION 7 — FINAL CTA
        ═══════════════════════════════════════════════ */}
        <section style={{ padding: '80px 24px 120px', maxWidth: '1280px', margin: '0 auto' }}>
          <Fade>
            <div style={{
              textAlign: 'center', padding: '80px 40px',
              borderRadius: '28px', position: 'relative', overflow: 'hidden',
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'linear-gradient(160deg, rgba(59,130,246,0.06) 0%, rgba(3,7,18,0.95) 50%, rgba(16,185,129,0.06) 100%)',
              backdropFilter: 'blur(20px)',
              boxShadow: '0 0 100px rgba(59,130,246,0.06), inset 0 1px 0 rgba(255,255,255,0.06)',
            }}>
              {/* Background orbs */}
              <div style={{ position: 'absolute', top: '-80px', left: '20%', width: '400px', height: '400px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(59,130,246,0.1), transparent 70%)', pointerEvents: 'none' }} />
              <div style={{ position: 'absolute', bottom: '-80px', right: '20%', width: '400px', height: '400px', borderRadius: '50%', background: 'radial-gradient(circle, rgba(16,185,129,0.1), transparent 70%)', pointerEvents: 'none' }} />



              <div style={{ position: 'relative', zIndex: 1 }}>
                <Sparkles size={32} color="#f59e0b" style={{ margin: '0 auto 24px', display: 'block' }} />
                <h2 style={{ fontSize: 'clamp(28px, 4vw, 52px)', fontWeight: 900, letterSpacing: '-0.03em', marginBottom: '16px', color: '#f8fafc' }}>
                  One Platform.<br />
                  <span className="hero-gradient-text">Two Connected Workflows.</span>
                </h2>
                <p style={{ fontSize: '16px', color: '#64748b', maxWidth: '480px', margin: '0 auto 40px', lineHeight: 1.75 }}>
                  Give hospitals and insurance teams the tools they need to move claims from submission to decision — faster.
                </p>
                <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => scrollTo('portals')}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '16px 32px', borderRadius: '14px',
                      background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                      border: 'none', color: '#fff', fontWeight: 700, fontSize: '15px',
                      cursor: 'pointer', boxShadow: '0 0 30px rgba(59,130,246,0.3)',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)'; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)'; }}
                  >
                    Get Started <ArrowRight size={16} />
                  </button>
                </div>
              </div>
            </div>
          </Fade>
        </section>

      </main>

      {/* ─── EXPANDED FOOTER (NEW) ─── */}
      <footer style={{ borderTop: '1px solid rgba(255,255,255,0.06)', padding: '80px 24px 40px', background: '#020617', position: 'relative', zIndex: 10 }}>
        <div style={{ maxWidth: '1280px', margin: '0 auto' }}>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '64px', justifyContent: 'space-between', marginBottom: '80px' }}>
            <div style={{ maxWidth: '320px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'linear-gradient(135deg, #3b82f6, #10b981)', padding: '1px' }}>
                  <div style={{ width: '100%', height: '100%', borderRadius: '7px', background: '#030712', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Activity size={16} color="#60a5fa" />
                  </div>
                </div>
                <span style={{ fontWeight: 800, fontSize: '18px', color: '#f1f5f9' }}>ORCA PolicyAI</span>
              </div>
              <p style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.6, marginBottom: '24px' }}>
                Enterprise-grade AI platform designed to automate healthcare prior authorizations, bridging the gap between hospital submissions and payer decisions.
              </p>
              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
                  <span style={{ fontSize: '14px', color: '#94a3b8' }}>𝕏</span>
                </div>
                <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
                  <span style={{ fontSize: '14px', color: '#94a3b8', fontWeight: 'bold' }}>in</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '80px', flexWrap: 'wrap' }}>
              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9', marginBottom: '20px' }}>Product</h4>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {['Hospital Portal', 'Insurance Portal', 'AI Engine', 'Integrations'].map(link => (
                    <li key={link}><a href="#" style={{ color: '#64748b', textDecoration: 'none', fontSize: '14px', transition: 'color 0.2s' }} onMouseEnter={e => e.currentTarget.style.color = '#38bdf8'} onMouseLeave={e => e.currentTarget.style.color = '#64748b'}>{link}</a></li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9', marginBottom: '20px' }}>Resources</h4>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {['Documentation', 'API Reference', 'Case Studies', 'System Status'].map(link => (
                    <li key={link}><a href="#" style={{ color: '#64748b', textDecoration: 'none', fontSize: '14px', transition: 'color 0.2s' }} onMouseEnter={e => e.currentTarget.style.color = '#38bdf8'} onMouseLeave={e => e.currentTarget.style.color = '#64748b'}>{link}</a></li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#f1f5f9', marginBottom: '20px' }}>Company</h4>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {['About Us', 'Careers', 'Security (SOC 2)', 'Contact'].map(link => (
                    <li key={link}><a href="#" style={{ color: '#64748b', textDecoration: 'none', fontSize: '14px', transition: 'color 0.2s' }} onMouseEnter={e => e.currentTarget.style.color = '#38bdf8'} onMouseLeave={e => e.currentTarget.style.color = '#64748b'}>{link}</a></li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '32px' }}>
            <div style={{ fontSize: '13px', color: '#475569' }}>
              © {new Date().getFullYear()} ORCA PolicyAI. All rights reserved.
            </div>
            <div style={{ display: 'flex', gap: '24px', fontSize: '13px', color: '#475569' }}>
              <a href="#" style={{ color: 'inherit', textDecoration: 'none' }}>Privacy Policy</a>
              <a href="#" style={{ color: 'inherit', textDecoration: 'none' }}>Terms of Service</a>
              <a href="#" style={{ color: 'inherit', textDecoration: 'none' }}>Cookie Policy</a>
            </div>
          </div>

        </div>
      </footer>

      {/* ─── AUTHENTICATION MODAL ─── */}
      {showSignIn && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px', background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}>
          <div style={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: '24px', padding: '32px', width: '100%', maxWidth: '440px', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)', animation: 'fade-in-up 0.3s ease-out' }}>

            {authStep === 'credentials' && (
              <>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', background: '#1e293b', padding: '4px', borderRadius: '12px' }}>
                  <button
                    onClick={() => setAuthMode('signin')}
                    style={{ flex: 1, padding: '10px', borderRadius: '8px', border: 'none', background: authMode === 'signin' ? '#334155' : 'transparent', color: authMode === 'signin' ? '#fff' : '#94a3b8', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' }}
                  >
                    Sign In
                  </button>
                  <button
                    onClick={() => setAuthMode('signup')}
                    style={{ flex: 1, padding: '10px', borderRadius: '8px', border: 'none', background: authMode === 'signup' ? '#334155' : 'transparent', color: authMode === 'signup' ? '#fff' : '#94a3b8', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s' }}
                  >
                    Sign Up
                  </button>
                </div>

                <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#f8fafc', marginBottom: '8px' }}>
                  {authMode === 'signin' ? 'Welcome Back' : 'Create Account'}
                </h3>
                <p style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '24px' }}>
                  {authMode === 'signin' ? 'Enter your credentials to access the workspace.' : 'Sign up to access the ORCA PolicyAI platform.'}
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {authMode === 'signup' && (
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Username</label>
                      <input
                        type="text"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        style={{ width: '100%', background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '12px 16px', color: '#f8fafc', outline: 'none' }}
                        placeholder="Dr. John Doe"
                      />
                    </div>
                  )}
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Email Address</label>
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      style={{ width: '100%', background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '12px 16px', color: '#f8fafc', outline: 'none' }}
                      placeholder="user@example.com"
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Password</label>
                    <input
                      type="password"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      style={{ width: '100%', background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '12px 16px', color: '#f8fafc', outline: 'none' }}
                      placeholder="••••••••"
                    />
                  </div>
                  {authMode === 'signup' && (
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Confirm Password</label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={e => setConfirmPassword(e.target.value)}
                        style={{ width: '100%', background: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '12px 16px', color: '#f8fafc', outline: 'none' }}
                        placeholder="••••••••"
                      />
                    </div>
                  )}
                  {errorMsg && (
                    <div style={{ color: '#f87171', fontSize: '13px', marginTop: '4px', fontWeight: 500 }}>
                      {errorMsg}
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '12px', marginTop: '32px' }}>
                  <button
                    onClick={() => setShowSignIn(false)}
                    style={{ flex: 1, padding: '12px 16px', borderRadius: '12px', background: '#1e293b', color: '#f8fafc', fontWeight: 600, border: 'none', cursor: 'pointer' }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleContinue}
                    disabled={authMode === 'signin' ? (!email || !password) : (!username || !email || !password || !confirmPassword)}
                    style={{
                      flex: 1, padding: '12px 16px', borderRadius: '12px',
                      background: (authMode === 'signin' ? (!email || !password) : (!username || !email || !password || !confirmPassword)) ? '#334155' : 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
                      color: (authMode === 'signin' ? (!email || !password) : (!username || !email || !password || !confirmPassword)) ? '#94a3b8' : '#fff',
                      fontWeight: 600, border: 'none', cursor: (authMode === 'signin' ? (!email || !password) : (!username || !email || !password || !confirmPassword)) ? 'not-allowed' : 'pointer'
                    }}
                  >
                    Continue
                  </button>
                </div>
              </>
            )}

            {authStep === 'portal' && (
              <>
                <h3 style={{ fontSize: '24px', fontWeight: 800, color: '#f8fafc', marginBottom: '8px' }}>Select Workspace</h3>
                <p style={{ fontSize: '14px', color: '#94a3b8', marginBottom: '24px' }}>Which portal do you want to move to?</p>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px' }}>
                  <button
                    onClick={() => selectPortal('hospital')}
                    style={{
                      padding: '20px', borderRadius: '16px', border: '1px solid #334155',
                      background: '#1e293b',
                      display: 'flex', alignItems: 'center', gap: '16px', cursor: 'pointer', transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = '#10b981'; e.currentTarget.style.background = 'rgba(16,185,129,0.1)'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = '#334155'; e.currentTarget.style.background = '#1e293b'; }}
                  >
                    <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(16,185,129,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Building2 size={24} color="#34d399" />
                    </div>
                    <div style={{ textAlign: 'left' }}>
                      <span style={{ display: 'block', fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>Hospital Portal</span>
                      <span style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>Submit claims and track authorizations</span>
                    </div>
                  </button>
                  <button
                    onClick={() => selectPortal('insurance')}
                    style={{
                      padding: '20px', borderRadius: '16px', border: '1px solid #334155',
                      background: '#1e293b',
                      display: 'flex', alignItems: 'center', gap: '16px', cursor: 'pointer', transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = '#3b82f6'; e.currentTarget.style.background = 'rgba(59,130,246,0.1)'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = '#334155'; e.currentTarget.style.background = '#1e293b'; }}
                  >
                    <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(59,130,246,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <ShieldCheck size={24} color="#60a5fa" />
                    </div>
                    <div style={{ textAlign: 'left' }}>
                      <span style={{ display: 'block', fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>Insurance Portal</span>
                      <span style={{ display: 'block', fontSize: '13px', color: '#94a3b8', marginTop: '4px' }}>Review claims and make decisions</span>
                    </div>
                  </button>
                </div>

                <div style={{ marginTop: '32px' }}>
                  <button
                    onClick={() => setAuthStep('credentials')}
                    style={{ width: '100%', padding: '12px 16px', borderRadius: '12px', background: 'transparent', color: '#94a3b8', fontWeight: 600, border: '1px solid #334155', cursor: 'pointer' }}
                  >
                    Back
                  </button>
                </div>
              </>
            )}

          </div>
        </div>
      )}

    </div>
  );
}
