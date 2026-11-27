import React, { useState } from 'react';
import StatusBadge from './StatusBadge';
import ScoreBar from './ScoreBar';
import { Play, Sparkles, AlertCircle, Layers, Shuffle, ShieldAlert, ShieldCheck, HelpCircle } from 'lucide-react';
import { ingestEmail } from '../api';

// 1. LOW AMBIGUITY POOL (Expected score in [0.06, 0.25))
const AMBIGUOUS_LOW_POOL = [
  {
    title: 'Vendor Billing Statement PDF',
    tierLabel: 'Low Threat (~0.06 - 0.20)',
    tier: 'low',
    create: (id, token) => ({
      subject: `Notice: Quarterly vendor report statement #${id}`,
      sender: `statements@invoices.global-logistics.com`,
      body: `Hello team,\n\nThe finalized shipping reconciliation statement for period #${id} has been compiled and uploaded for review.\nPlease download and archive the attached statement: https://invoices.global-logistics.com/download/pdf/stmt_${id}?auth=${token}\n\nRegards,\nGlobal Logistics Billing Operations`
    })
  },
  {
    title: 'IT Helpdesk Ticket Resolution',
    tierLabel: 'Low Threat (~0.06 - 0.20)',
    tier: 'low',
    create: (id, token) => ({
      subject: `Support Ticket #${id} Update: Resolution Pending Approval`,
      sender: `helpdesk@support.ticket-resolution.net`,
      body: `Dear customer,\n\nYour service ticket #${id} regarding access permissions has been updated.\nPlease review the proposed resolution notes here: https://support.ticket-resolution.net/ticket/${id}?auth=${token}\n\nBest regards,\nIT Service Desk`
    })
  },
  {
    title: 'Vendor Compliance Audit Checklist',
    tierLabel: 'Low Threat (~0.06 - 0.20)',
    tier: 'low',
    create: (id, token) => ({
      subject: `Vendor Compliance Audit: Q${(id % 4) + 1} Checklist #${id}`,
      sender: `compliance-audit@review.vendor-compliance.org`,
      body: `All external vendors are requested to verify their active compliance certification for this quarter.\nReview the compliance checklist portal: https://review.vendor-compliance.org/audit/q${(id % 4) + 1}_checklist?vendor=${id}\n\nCompliance Management Office`
    })
  },
  {
    title: 'Engineering Wiki Release Notes',
    tierLabel: 'Low Threat (~0.06 - 0.20)',
    tier: 'low',
    create: (id, token) => ({
      subject: `Engineering Architecture Release Notes v2.${id % 10}`,
      sender: `devops@internal-wiki.project-docs.org`,
      body: `Team,\n\nThe system release notes and deployment dependencies for sprint #${id} are published.\nPlease review before Friday's deployment call: https://internal-wiki.project-docs.org/release/notes-v2.${id % 10}?ref=${token}\n\nDevOps Core Team`
    })
  },
  {
    title: 'Joint Venture Executive Summary',
    tierLabel: 'Low Threat (~0.06 - 0.20)',
    tier: 'low',
    create: (id, token) => ({
      subject: `Shared Partner Financial Summary Q${(id % 4) + 1} #${id}`,
      sender: `reporting@files.acme-corp-partners.org`,
      body: `Attached is the quarterly joint venture executive summary.\nAccess the document on the partner file share: https://files.acme-corp-partners.org/reports/q${(id % 4) + 1}_summary_${id}.pdf?token=${token}\n\nPartner Relations`
    })
  }
];

// 2. MID AMBIGUITY POOL (Expected score in [0.35, 0.55))
const AMBIGUOUS_MID_POOL = [
  {
    title: 'Client Case Review Dossier',
    tierLabel: 'Mid Threat (~0.35 - 0.55)',
    tier: 'mid',
    create: (id, token) => ({
      subject: `Client Services Portal: Case Review #${id}`,
      sender: `cases@portal.client-services-hub.com`,
      body: `A new client inquiry case has been assigned to your department for resolution.\nPlease inspect the client case dossier and log your response: https://portal.client-services-hub.com/dashboard/case_${id}?view=active&tok=${token}\n\nClient Operations Manager`
    })
  },
  {
    title: 'Finance Statement Portal Link',
    tierLabel: 'Mid Threat (~0.35 - 0.55)',
    tier: 'mid',
    create: (id, token) => ({
      subject: `Action Required: Statement from Vendor #${id}`,
      sender: `billing@shared.finance-documents.net`,
      body: `Please review your outstanding monthly billing statement attached below.\nAccess the client statement here: https://shared.finance-documents.net/statements/may2026?token=${token}&id=${id}\n\nAccounting Department`
    })
  },
  {
    title: 'Logistics Manifest Tracking Portal',
    tierLabel: 'Mid Threat (~0.35 - 0.55)',
    tier: 'mid',
    create: (id, token) => ({
      subject: `Logistics Dispatch: Consignment #${id} In-Transit Update`,
      sender: `tracking@docs.logistics-tracking-portal.com`,
      body: `Your corporate equipment shipment has been dispatched.\nTrack the real-time manifest and delivery status here: https://docs.logistics-tracking-portal.com/shipment/status?track=${token}&pkg=${id}\n\nLogistics Dispatch Center`
    })
  },
  {
    title: 'Corporate SSO Gateway Reconnect',
    tierLabel: 'Mid Threat (~0.35 - 0.55)',
    tier: 'mid',
    create: (id, token) => ({
      subject: `Single Sign-On (SSO) Session Renewal Notice #${id}`,
      sender: `iam-security@auth-hub.corp-network.org`,
      body: `Your organizational federated authentication session is due for periodic validation.\nPlease reconnect via the corporate gateway: https://auth-hub.corp-network.org/sso/redirect?target=hub&session=${token}\n\nIdentity & Access Management`
    })
  },
  {
    title: 'Cloud Deliverables Shared Folder',
    tierLabel: 'Mid Threat (~0.35 - 0.55)',
    tier: 'mid',
    create: (id, token) => ({
      subject: `Shared Folder: Project Deliverables Archive #${id}`,
      sender: `cloud-share@cloud-storage-preview.com`,
      body: `External client has shared an asset bundle with your work account.\nYou can preview and review the folder items here: https://cloud-storage-preview.com/share/folder/${id}?auth=temp&token=${token}\n\nCollaboration Services`
    })
  }
];

// 3. HIGH AMBIGUITY POOL (Expected score in [0.65, 0.84) - Edge Cases)
const AMBIGUOUS_HIGH_POOL = [
  {
    title: 'Encrypted Contract Review Portal',
    tierLabel: 'High Threat Edge Case (~0.65 - 0.84)',
    tier: 'high',
    create: (id, token) => ({
      subject: `Document Verification Required: Secure Contract #${id}`,
      sender: `contracts@secure-docs-share.me`,
      body: `You have received an encrypted contract draft awaiting sign-off.\nPlease authenticate and review the contract details: https://secure-docs-share.me/review/file_${id}?access=${token}\n\nContracts Admin`
    })
  },
  {
    title: 'Ambiguous Vendor Invoice',
    tierLabel: 'High Threat Edge Case (~0.65 - 0.84)',
    tier: 'high',
    create: (id, token) => ({
      subject: `Action Required: Statement from Vendor #${id}`,
      sender: `billing@accounting-docs.co`,
      body: `Please review the updated service invoice attached here: https://portal.billing-docs.co/invoices/client/${id}/review?token=${token}\n\nAccounts Payable Team`
    })
  },
  {
    title: 'Partner Supplier ID Verification',
    tierLabel: 'High Threat Edge Case (~0.65 - 0.84)',
    tier: 'high',
    create: (id, token) => ({
      subject: `Partner Access Verification: Confirm Organization ID #${id}`,
      sender: `security@verify-partner-id.cc`,
      body: `Your third-party supplier token must be confirmed before midnight.\nConfirm credentials at the partner portal: https://verify-partner-id.cc/docs/vendor/login?ref=${id}&tok=${token}\n\nSupplier Security Desk`
    })
  },
  {
    title: 'HR Employee Payroll Verification Portal',
    tierLabel: 'High Threat Edge Case (~0.65 - 0.84)',
    tier: 'high',
    create: (id, token) => ({
      subject: `Payroll & Tax Statement Available for Review [Notice #${id}]`,
      sender: `hr-payroll@payroll-employee-service.co`,
      body: `Your updated tax withholding summary for the pay period is ready.\nPlease login to inspect your pay slip: https://payroll-employee-service.co/portal/login?employee=${id}&session=${token}\n\nHuman Resources`
    })
  },
  {
    title: 'Multi-Subdomain Client Auth Gateway',
    tierLabel: 'High Threat Edge Case (~0.65 - 0.84)',
    tier: 'high',
    create: (id, token) => ({
      subject: `Client Portal Auth: Session Re-Authentication Required #${id}`,
      sender: `auth-service@auth.services.client-portal.net`,
      body: `We noticed an authentication request from an unrecognized device.\nPlease verify your user identity at: https://auth.services.client-portal.net/login/step1?user=${id}&token=${token}\n\nClient Security Team`
    })
  },
  {
    title: 'Cloud Drive Shared Document Preview',
    tierLabel: 'High Threat Edge Case (~0.65 - 0.84)',
    tier: 'high',
    create: (id, token) => ({
      subject: `Confidential Document Shared: Drive Preview Notice #${id}`,
      sender: `no-reply@drive-share-cloud.net`,
      body: `A shared cloud document has been sent to your inbox.\nClick here to preview the document online: https://drive-share-cloud.net/preview/docs?id=${id}&view=web&token=${token}\n\nCloud Document Management`
    })
  }
];

// HIGH RISK POOL (Expected score >= 0.85 -> Auto-Quarantine)
const HIGH_RISK_POOL = [
  {
    title: 'PayPal Credential Harvester',
    create: (id, token) => ({
      subject: `URGENT: Your PayPal account access has been suspended [Case #${id}]`,
      sender: `security-notice@paypal-verification.pages.dev`,
      body: `Your account has been locked due to multiple unauthorized logins.\nPlease verify your credentials immediately to avoid permanent termination: http://paypal-verification-update.secure-login-account.pages.dev/banking/signin.php?token=${token}&case=${id}\n\nSecurity Operations`
    })
  },
  {
    title: 'Apple ID Security Alert',
    create: (id, token) => ({
      subject: `Apple ID Critical Alert: Account Lockout Warning #${id}`,
      sender: `appleid-support@appleid-verify-user.cc`,
      body: `Your Apple ID was recently accessed from an unrecognized browser in Moscow, Russia.\nVerify your identity immediately to prevent lockout: http://appleid-verify-user.cc/account/security/auth.php?case=${id}&tok=${token}\n\nApple Support Team`
    })
  },
  {
    title: 'Microsoft 365 Credential Phish',
    create: (id, token) => ({
      subject: `Microsoft 365: Urgent Password Expiration Notice #${id}`,
      sender: `admin@update-bank-security.top`,
      body: `Your corporate Microsoft 365 password will expire in 2 hours.\nKeep your current password by confirming it here: http://update-bank-security.top/m365/login/verify.html?usr=${id}&tok=${token}\n\nIT Support Systems`
    })
  },
  {
    title: 'Crypto Wallet Recovery Theft',
    create: (id, token) => ({
      subject: `Crypto Wallet Security Warning: Unauthorized Withdrawal Attempt #${id}`,
      sender: `alerts@crypto-wallet-recovery.com`,
      body: `A withdrawal of 2.45 ETH was requested from your wallet address.\nIf this was not you, cancel the transaction immediately: http://crypto-wallet-recovery.com/auth/wallet/token/recovery?session=${token}&id=${id}\n\nWallet Security Guard`
    })
  },
  {
    title: 'Banking Session Expiration Alert',
    create: (id, token) => ({
      subject: `Online Banking Security: Immediate Session Authentication Required #${id}`,
      sender: `fraud-alert@online-banking-auth.info`,
      body: `We detected unusual wire transfer activity on your corporate account.\nAuthenticate your mobile session immediately: http://online-banking-auth.info/secure/session/update.php?id=${id}&token=${token}\n\nFraud Detection Unit`
    })
  }
];

// LOW RISK POOL (Expected score < 0.05 -> Auto-Allow)
const LOW_RISK_POOL = [
  {
    title: 'Wikipedia Cybersecurity Research',
    create: (id) => ({
      subject: `Engineering Architecture Sync & Style Guide Review #${id}`,
      sender: `alex@internal-tools.org`,
      body: `Team, please review the latest updates on the documentation wiki before our planning call:\nhttps://wikipedia.org/wiki/Phishing\n\nThanks,\nAlex`
    })
  },
  {
    title: 'GitHub Pull Request Discussion',
    create: (id) => ({
      subject: `Open Source Kernel Pull Request Review #${id}`,
      sender: `maintainer@github.com`,
      body: `Hey developers,\n\nPlease check the discussion on the upstream kernel patch here:\nhttps://github.com/torvalds/linux/pull/${id}\n\nLinux Kernel Contributors`
    })
  },
  {
    title: 'StackOverflow Technical Reference',
    create: (id) => ({
      subject: `StackOverflow Solution for API Async Context #${id}`,
      sender: `dev-team@stackoverflow.com`,
      body: `Here is the reference thread explaining how to avoid asyncio deadlocks in Python 3.12:\nhttps://stackoverflow.com/questions/${id}/python-fastapi-cors\n\nBest,\nDev Lead`
    })
  },
  {
    title: 'Python Software Foundation Docs',
    create: (id) => ({
      subject: `Official Documentation: Standard Library Email Parser v3.12`,
      sender: `python-docs@python.org`,
      body: `Team, the standard library documentation for RFC 822 email headers has been updated:\nhttps://docs.python.org/3/library/email.html\n\nPython Software Foundation`
    })
  },
  {
    title: 'Internal Team Coffee Sync (Clean Text)',
    create: (id) => ({
      subject: `Team Coffee & Project Retro Sync #${id}`,
      sender: `sarah@company.internal`,
      body: `Hi everyone,\n\nLet's grab a coffee at 2 PM today in the 3rd floor cafeteria to discuss the sprint deliverables.\nNo preparation required, see you all there!\n\nSarah`
    })
  }
];

export default function SandboxTab({ onEmailIngested }) {
  // Preset state tracking
  const [activeCategory, setActiveCategory] = useState('ambiguous');
  const [ambiguousSubTier, setAmbiguousSubTier] = useState('all');
  const [activeVariantName, setActiveVariantName] = useState('Ambiguous Vendor Invoice');
  const [activeTierBadge, setActiveTierBadge] = useState('Review Band [0.05, 0.85)');

  // Form inputs
  const initialEmail = AMBIGUOUS_HIGH_POOL[1].create(9821, 'token_8841');
  const [subject, setSubject] = useState(initialEmail.subject);
  const [sender, setSender] = useState(initialEmail.sender);
  const [body, setBody] = useState(initialEmail.body);

  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Helper to generate a random 4-digit ID and token
  const getRandomParams = () => {
    const id = Math.floor(1000 + Math.random() * 9000);
    const token = Math.random().toString(36).substring(2, 8);
    return { id, token };
  };

  // Generator function that produces a unique, fresh email variant
  const generateEmail = (category = activeCategory, subTier = ambiguousSubTier) => {
    const { id, token } = getRandomParams();
    let template;
    let tierText = '';

    if (category === 'high') {
      const idx = Math.floor(Math.random() * HIGH_RISK_POOL.length);
      template = HIGH_RISK_POOL[idx];
      tierText = 'High Threat (Auto-Quarantine ≥ 0.85)';
      const payload = template.create(id, token);
      setSubject(payload.subject);
      setSender(payload.sender);
      setBody(payload.body);
      setActiveVariantName(template.title);
      setActiveTierBadge(tierText);
    } else if (category === 'low') {
      const idx = Math.floor(Math.random() * LOW_RISK_POOL.length);
      template = LOW_RISK_POOL[idx];
      tierText = 'Safe Traffic (Auto-Allow < 0.05)';
      const payload = template.create(id, token);
      setSubject(payload.subject);
      setSender(payload.sender);
      setBody(payload.body);
      setActiveVariantName(template.title);
      setActiveTierBadge(tierText);
    } else {
      // Ambiguous Category: Handle sub-tiers (all, low, mid, high)
      let pool;
      if (subTier === 'low') {
        pool = AMBIGUOUS_LOW_POOL;
        tierText = 'Ambiguous • Low Threat (~0.06 - 0.20)';
      } else if (subTier === 'mid') {
        pool = AMBIGUOUS_MID_POOL;
        tierText = 'Ambiguous • Mid Threat (~0.35 - 0.55)';
      } else if (subTier === 'high') {
        pool = AMBIGUOUS_HIGH_POOL;
        tierText = 'Ambiguous • High Threat (~0.65 - 0.84)';
      } else {
        // Combined pool with weighted or random selection across all ambiguous levels
        const allAmbiguous = [
          ...AMBIGUOUS_LOW_POOL,
          ...AMBIGUOUS_MID_POOL,
          ...AMBIGUOUS_HIGH_POOL
        ];
        pool = allAmbiguous;
      }

      const idx = Math.floor(Math.random() * pool.length);
      template = pool[idx];
      tierText = template.tierLabel || 'Ambiguous Review Band [0.05, 0.85)';
      const payload = template.create(id, token);

      setSubject(payload.subject);
      setSender(payload.sender);
      setBody(payload.body);
      setActiveVariantName(template.title);
      setActiveTierBadge(tierText);
    }

    // Reset previous execution results on generating a fresh variant
    setResult(null);
    setErrorMsg(null);
  };

  const handleSelectCategory = (cat) => {
    setActiveCategory(cat);
    generateEmail(cat, ambiguousSubTier);
  };

  const handleSelectAmbiguousSubTier = (tier) => {
    setAmbiguousSubTier(tier);
    setActiveCategory('ambiguous');
    generateEmail('ambiguous', tier);
  };

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!subject || !sender || !body) {
      setErrorMsg('All fields (Subject, Sender, Body) are required.');
      return;
    }

    try {
      setIsProcessing(true);
      setErrorMsg(null);
      const res = await ingestEmail({
        subject: subject.trim(),
        sender: sender.trim(),
        body: body.trim()
      });
      setResult(res);
      onEmailIngested?.();
    } catch (err) {
      setErrorMsg(err.message || 'Ingestion failed');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Header & Dynamic Generator Controls */}
      <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <span>Interactive Multi-Agent Stream Sandbox</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Generate different email variants across all threat bands and dispatch them through the 6-agent pipeline in real-time.
            </p>
          </div>

          {/* Quick Shuffle Button */}
          <button
            type="button"
            onClick={() => generateEmail(activeCategory, ambiguousSubTier)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition active:scale-95 shadow-sm"
          >
            <Shuffle className="w-3.5 h-3.5" />
            <span>Generate Different Email</span>
          </button>
        </div>

        {/* Primary Threat Category Selector */}
        <div>
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
            Select Threat Archetype (Click to regenerate a new variant)
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => handleSelectCategory('ambiguous')}
              className={`text-xs px-3.5 py-1.5 rounded-xl border font-medium transition flex items-center gap-1.5 ${
                activeCategory === 'ambiguous'
                  ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-sm'
                  : 'border-white/10 bg-[#070A12] hover:bg-[#121B30] text-slate-300'
              }`}
            >
              <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
              <span>Ambiguous Edge Cases (Review Band)</span>
            </button>

            <button
              type="button"
              onClick={() => handleSelectCategory('high')}
              className={`text-xs px-3.5 py-1.5 rounded-xl border font-medium transition flex items-center gap-1.5 ${
                activeCategory === 'high'
                  ? 'bg-red-500/20 border-red-500/50 text-red-300 shadow-sm'
                  : 'border-white/10 bg-[#070A12] hover:bg-[#121B30] text-slate-300'
              }`}
            >
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
              <span>Credential Harvester (High Risk ≥ 0.85)</span>
            </button>

            <button
              type="button"
              onClick={() => handleSelectCategory('low')}
              className={`text-xs px-3.5 py-1.5 rounded-xl border font-medium transition flex items-center gap-1.5 ${
                activeCategory === 'low'
                  ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-sm'
                  : 'border-white/10 bg-[#070A12] hover:bg-[#121B30] text-slate-300'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Legitimate Memo (Low Risk &lt; 0.05)</span>
            </button>
          </div>
        </div>

        {/* Ambiguous Threat Spectrum Sub-Tiers */}
        {activeCategory === 'ambiguous' && (
          <div className="pt-3 border-t border-white/5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Ambiguous Threat Sub-Levels (Explore the 0.05 - 0.85 Spectrum):
              </span>
              <span className="text-[11px] font-mono text-amber-400/90 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                Routed to SecOps Review Queue
              </span>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handleSelectAmbiguousSubTier('all')}
                className={`text-[11px] px-3 py-1 rounded-lg border font-mono transition ${
                  ambiguousSubTier === 'all'
                    ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300'
                    : 'bg-[#070A12] border-white/10 text-slate-400 hover:text-slate-200'
                }`}
              >
                🎲 Random Ambiguous Spectrum
              </button>

              <button
                type="button"
                onClick={() => handleSelectAmbiguousSubTier('low')}
                className={`text-[11px] px-3 py-1 rounded-lg border font-mono transition ${
                  ambiguousSubTier === 'low'
                    ? 'bg-amber-500/25 border-amber-500/50 text-amber-200'
                    : 'bg-[#070A12] border-white/10 text-slate-400 hover:text-slate-200'
                }`}
              >
                1. Low Ambiguity (~0.06 - 0.20)
              </button>

              <button
                type="button"
                onClick={() => handleSelectAmbiguousSubTier('mid')}
                className={`text-[11px] px-3 py-1 rounded-lg border font-mono transition ${
                  ambiguousSubTier === 'mid'
                    ? 'bg-amber-500/25 border-amber-500/50 text-amber-200'
                    : 'bg-[#070A12] border-white/10 text-slate-400 hover:text-slate-200'
                }`}
              >
                2. Mid Ambiguity (~0.35 - 0.55)
              </button>

              <button
                type="button"
                onClick={() => handleSelectAmbiguousSubTier('high')}
                className={`text-[11px] px-3 py-1 rounded-lg border font-mono transition ${
                  ambiguousSubTier === 'high'
                    ? 'bg-amber-500/25 border-amber-500/50 text-amber-200'
                    : 'bg-[#070A12] border-white/10 text-slate-400 hover:text-slate-200'
                }`}
              >
                3. High Edge Case (~0.65 - 0.84)
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Main Grid: Input Form vs Output Result */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Form (6 cols) */}
        <form onSubmit={handleIngest} className="lg:col-span-6 bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold text-slate-200 uppercase tracking-wider">
              Test Email Payload
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-cyan-300 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-500/30">
                {activeVariantName}
              </span>
              <span className="text-[10px] font-mono text-slate-400 bg-white/5 px-2 py-0.5 rounded border border-white/10">
                {activeTierBadge}
              </span>
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full bg-[#070A12] border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Sender Address</label>
            <input
              type="text"
              value={sender}
              onChange={(e) => setSender(e.target.value)}
              className="w-full bg-[#070A12] border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Email Body (With Embedded Links)</label>
            <textarea
              rows={5}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="w-full bg-[#070A12] border border-white/10 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 resize-none font-sans"
            />
          </div>

          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={() => generateEmail(activeCategory, ambiguousSubTier)}
              className="px-3 py-2.5 rounded-xl border border-white/10 bg-[#070A12] hover:bg-[#121B30] text-slate-300 text-xs font-semibold transition flex items-center justify-center gap-1.5"
              title="Generate another variant"
            >
              <Shuffle className="w-3.5 h-3.5 text-indigo-400" />
              <span>Shuffle</span>
            </button>

            <button
              type="submit"
              disabled={isProcessing}
              className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-xs shadow-lg shadow-indigo-600/30 transition flex items-center justify-center gap-2"
            >
              <Play className={`w-3.5 h-3.5 ${isProcessing ? 'animate-spin' : ''}`} />
              <span>{isProcessing ? 'Executing 6-Agent Pipeline...' : 'Run Pipeline Ingestion'}</span>
            </button>
          </div>
        </form>

        {/* Right Output Dossier (6 cols) */}
        <div className="lg:col-span-6">
          {!result ? (
            <div className="h-full min-h-[360px] flex flex-col items-center justify-center p-8 text-center text-slate-500 bg-[#0D1424]/40 border border-white/5 rounded-2xl">
              <Layers className="w-10 h-10 stroke-[1.25] text-slate-600 mb-2" />
              <div className="text-xs font-semibold text-slate-300">Awaiting Pipeline Execution</div>
              <p className="text-[11px] text-slate-500 max-w-xs mt-1">
                Click "Run Pipeline Ingestion" to dispatch this message through the multi-agent detection pipeline.
              </p>
            </div>
          ) : (
            <div className="bg-[#0D1424] border border-white/10 rounded-2xl p-5 shadow-lg space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-white/5">
                <div>
                  <span className="font-mono text-xs font-bold text-indigo-400">{result.id}</span>
                  <div className="text-[11px] text-slate-400 font-mono">Assigned UUID</div>
                </div>
                <StatusBadge status={result.automated_decision} />
              </div>

              <div>
                <div className="text-xs text-slate-400 font-medium mb-1">Max Risk Score:</div>
                <ScoreBar score={result.max_score} />
              </div>

              {/* Step-by-Step Agent Log */}
              <div className="bg-[#070A12] border border-white/5 rounded-xl p-3.5 space-y-2 font-mono text-[11px]">
                <div className="text-slate-400 font-bold uppercase tracking-wider font-sans mb-1 text-[10px]">
                  Agent Pipeline Execution Sequence
                </div>
                <div className="text-slate-300">
                  1. <strong className="text-cyan-400">ParserAgent</strong>: {result.urls?.length || 0} URL(s) extracted & defanged
                </div>
                <div className="text-slate-300">
                  2. <strong className="text-indigo-400">FeatureAgent</strong>: Extracted 26 lexical signals + Shannon entropy
                </div>
                <div className="text-slate-300">
                  3. <strong className="text-purple-400">ClassifierAgent</strong>: Max threat score {result.max_score?.toFixed(4)}
                </div>
                <div className="text-slate-300">
                  4. <strong className="text-amber-400">TriageAgent</strong>: Decision &rarr; <span className="text-white font-bold">{result.automated_decision}</span>
                </div>
                <div className="text-slate-300">
                  5. <strong className="text-emerald-400">ActionAgent</strong>: Persisted to SQLite transactional storage
                </div>
                <div className="text-slate-300">
                  6. <strong className="text-blue-400">AuditAgent</strong>: Audit trail logged & telemetry updated
                </div>
              </div>

              {/* Extracted URLs List */}
              {result.urls && result.urls.length > 0 && (
                <div>
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                    Defanged URL Payloads
                  </div>
                  <div className="space-y-2">
                    {result.urls.map((u, idx) => (
                      <div key={idx} className="bg-[#070A12] p-2.5 rounded-xl border border-white/5 text-xs font-mono">
                        <div className="text-cyan-300 break-all">{u.defanged_url}</div>
                        <div className="text-[11px] text-slate-500 mt-1">Score: {u.score?.toFixed(4)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

      </div>

    </div>
  );
}
