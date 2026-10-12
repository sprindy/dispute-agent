// ============================================================
// Ryde Dispute Resolution Agent — Client-Side Engine
// Full port of the Python backend to JavaScript
// ============================================================

// --- Config & Constants ---
const CONFIDENCE_WEIGHTS = {
    policy_clarity: 0.30, evidence_strength: 0.35,
    historical_consistency: 0.15, agent_consistency: 0.10, claim_reliability: 0.10,
};
const HIGH_CONF_THRESHOLD = 0.75, LOW_CONF_THRESHOLD = 0.45;
const HIGH_RISK_CATEGORIES = ['safety_incident'];
const CATEGORY_POLICY_MAP = {
    no_show_charge: ['CAN-01','CAN-02','CAN-06','CAN-07','CAN-09','CAN-10'],
    route_deviation: ['FARE-01','FARE-02','FARE-08','FARE-09'],
    cancellation_fee: ['CAN-01','CAN-04','CAN-05','CAN-06','CAN-07','CAN-09'],
    waiting_fee: ['CAN-03','CAN-08'],
    cleaning_fee: ['CLEAN-01','CLEAN-02','CLEAN-03','CLEAN-04','CLEAN-05','CLEAN-06'],
    fare_dispute: ['FARE-02','FARE-03','FARE-04','FARE-10','FARE-11','FARE-12','FARE-14'],
    safety_incident: ['SAFE-01','SAFE-02','SAFE-03','SAFE-04','SAFE-07','SAFE-08'],
};

// --- Policy Engine ---
class PolicyEngine {
    constructor() {
        this.snapshotId = POLICY_DATA.snapshot_id;
        this.rules = {}; this.conflicts = [];
        for (const r of POLICY_DATA.rules) this.rules[r.policy_id] = r;
        this.conflicts = POLICY_DATA.conflicts.map(c => ({...c, is_gap: c.id.startsWith('GAP')}));
    }
    getRule(pid) { return this.rules[pid] || null; }
    getRulesForCategory(cat) {
        return (CATEGORY_POLICY_MAP[cat]||[]).map(id => this.rules[id]).filter(r=>r);
    }
    getConflictsForPolicy(pid) {
        const rule = this.getRule(pid); if (!rule) return [];
        return this.conflicts.filter(c => c.source_ids.some(sid => rule.source_ids.includes(sid)));
    }
    allRuleIds() { return Object.keys(this.rules).sort(); }
    summary() {
        return {
            snapshot_id: this.snapshotId,
            total_rules: Object.keys(this.rules).length,
            total_conflicts: this.conflicts.filter(c=>!c.is_gap).length,
            total_gaps: this.conflicts.filter(c=>c.is_gap).length,
        };
    }
}

// --- Evidence ---
const isAvail = e => e.status==='available';
const EvidenceCollector = {
    validate(items) {
        const r = {total:items.length, available:0, missing:0, disputed:0, issues:[]};
        const seen = new Set();
        for (const it of items) {
            if(seen.has(it.evidence_id)) r.issues.push(`Duplicate: ${it.evidence_id}`);
            seen.add(it.evidence_id);
            if(isAvail(it)) r.available++; else if(it.status==='missing') r.missing++; else r.disputed++;
        }
        if(r.missing>0) r.issues.push(`${r.missing} missing — facts stay UNKNOWN`);
        if(r.disputed>0) r.issues.push(`${r.disputed} disputed — verification required`);
        return r;
    },
    extractFacts(items) {
        const f = {};
        for (const it of items) {
            if(isAvail(it)&&it.field) f[it.field]=it.value;
            else if(it.status==='disputed'&&it.field) f[it.field]={_disputed:true,value:it.value};
        }
        return f;
    }
};

// --- Agent helpers ---
function mkArg(role,liability,assess,rationale,pids,sids,eids,cf,remedy,warns) {
    return {agent_role:role,liability_label:liability,assessment:assess,rationale:rationale,
        policy_ids:pids||[],source_ids:sids||[],evidence_ids:eids||[],
        confidence_factors:cf||{},requested_remedy:remedy||null,warnings:warns||[],
        toDict(){return{agent_role:this.agent_role,liability_label:this.liability_label,assessment:this.assessment,rationale:this.rationale,policy_ids:this.policy_ids,source_ids:this.source_ids,evidence_ids:this.evidence_ids,confidence_factors:this.confidence_factors,requested_remedy:this.requested_remedy,warnings:this.warnings};}
    };
}
function collectSids(pe,pids){const r=[];for(const p of pids){const rule=pe.getRule(p);if(rule)for(const s of rule.source_ids)if(!r.includes(s))r.push(s);}return r;}
function checkConf(pe,pids){const w=[];for(const p of pids)for(const c of pe.getConflictsForPolicy(p))w.push(`${c.id} (${c.is_gap?'GAP':'CONFLICT'}): ${c.description}`);return w;}
function histNote(c){return`Historical ref (non-determinative): driver_rating=${c.driver_rating}, prior_rejected=${c.prior_rejected_disputes}. Affects confidence/routing only.`;}
function availEids(c){return c.evidence.filter(isAvail).map(e=>e.evidence_id);}

// --- Rider Advocate ---
const RiderAdvocate = {
    assess(pe,c) {
        const cat=c.category, f=c.facts, av=availEids(c);
        if(cat==='no_show_charge') {
            const pids=['CAN-01','CAN-02','CAN-06','CAN-10'], w=checkConf(pe,pids);
            const pa=f.pickup_arrival_verified, ws=f.wait_seconds, mc=f.match_to_cancel_seconds, ch=f.rider_charge_sgd;
            if(mc!=null&&mc<=180) return mkArg('rider_advocate','no_fault','policy_inconsistent',`Rider cancelled within 3-min grace (match_to_cancel=${mc}s, grace=180s). CAN-01: free. The ${ch} SGD charge should be flagged.`,pids,collectSids(pe,pids),av,{policy_clarity:0.95,evidence_strength:0.80},'waiver_review',w);
            if(pa===false) return mkArg('rider_advocate','driver_fault','policy_inconsistent','No-show requires arrival at booked pickup. GPS does not confirm driver arrival. Charge not supported.',['CAN-02'],collectSids(pe,['CAN-02']),av,{policy_clarity:0.90,evidence_strength:0.75},'charge_reversal',w);
            if(ws!=null&&ws<=180) return mkArg('rider_advocate','no_fault','policy_inconsistent',`Waiting ${ws}s; CAN-02 requires >180s. Charge doesn't meet threshold.`,['CAN-02'],collectSids(pe,['CAN-02']),av,{policy_clarity:0.90,evidence_strength:0.80},'charge_reversal',w);
            if(pa===true&&ws!=null&&ws>180) return mkArg('rider_advocate','rider_fault','policy_consistent',`Verified arrival and ${ws}s waiting exceed 3-min threshold (CAN-02). Charge is policy-consistent. Rider may request waiver under CAN-07.`,[...pids,'CAN-07'],collectSids(pe,[...pids,'CAN-07']),av,{policy_clarity:0.90,evidence_strength:0.85},'inform_rider_of_waiver_option',w);
            const miss=[]; if(pa==null)miss.push('pickup_arrival_verified'); if(ws==null)miss.push('wait_seconds');
            return mkArg('rider_advocate','insufficient_evidence','insufficient_evidence',`Cannot determine — missing: ${miss}.`,pids,collectSids(pe,pids),av,{policy_clarity:0.85,evidence_strength:0.30},null,[...w,histNote(c)]);
        }
        if(cat==='cancellation_fee') {
            const pids=['CAN-01','CAN-04','CAN-05','CAN-06'], w=checkConf(pe,pids);
            const mc=f.match_to_cancel_seconds, sb=f.seconds_before_schedule_at_cancel;
            if(sb!=null&&sb>900) return mkArg('rider_advocate','no_fault','policy_inconsistent',`Advance cancel ${sb}s before pickup >900s (15min). CAN-04: free.`,['CAN-04'],collectSids(pe,['CAN-04']),av,{policy_clarity:0.90,evidence_strength:0.80},'charge_reversal',w);
            if(mc!=null&&mc<=180) return mkArg('rider_advocate','no_fault','policy_inconsistent',`Cancel at ${mc}s < 3-min grace (CAN-01).`,['CAN-01'],collectSids(pe,['CAN-01']),av,{policy_clarity:0.95,evidence_strength:0.80},'charge_reversal',w);
            return mkArg('rider_advocate','insufficient_evidence','insufficient_evidence','Missing timing data.',pids,collectSids(pe,pids),av,{policy_clarity:0.80,evidence_strength:0.30},null,w);
        }
        if(cat==='route_deviation') {
            const pids=['FARE-01','FARE-02'], w=checkConf(pe,pids);
            const ch=f.base_fare_charged_sgd, qt=f.quoted_fare_sgd, ri=f.route_distance_increase_pct, rr=f.requested_refund_pct;
            if(ch!=null&&qt!=null&&ch>qt) return mkArg('rider_advocate','driver_fault','policy_inconsistent',`Quoted ${qt} but charged ${ch}. FARE-02: fares fixed.`,['FARE-02'],collectSids(pe,['FARE-02']),av,{policy_clarity:0.90,evidence_strength:0.85},'fare_review',w);
            if(rr!=null&&rr>0) return mkArg('rider_advocate','no_fault','unsupported_rule',`Rider requests ${rr}% refund for ${ri}% increase. No public formula (FARE-01).`,['FARE-01'],collectSids(pe,['FARE-01']),av,{policy_clarity:0.85,evidence_strength:0.70},null,w);
            return mkArg('rider_advocate','insufficient_evidence','insufficient_evidence','Insufficient fare data.',pids,collectSids(pe,pids),av,{policy_clarity:0.80,evidence_strength:0.30},null,w);
        }
        if(cat==='waiting_fee') {
            const pids=['CAN-03'], w=checkConf(pe,pids); const ws=f.wait_seconds, ch=f.rider_charge_sgd;
            if(ws!=null&&ws<=180) return mkArg('rider_advocate','no_fault','policy_inconsistent',`Wait ${ws}s <= 180s (CAN-03). Fee inconsistent.`,pids,collectSids(pe,pids),av,{policy_clarity:0.90,evidence_strength:0.80},'charge_review',w);
            return mkArg('rider_advocate','insufficient_evidence','insufficient_evidence','Insufficient waiting data.',pids,collectSids(pe,pids),av,{policy_clarity:0.85,evidence_strength:0.30},null,w);
        }
        if(cat==='fare_dispute') {
            const pids=['FARE-02','FARE-10','FARE-11','FARE-14'], w=checkConf(pe,pids);
            const pm=f.payment, pf=f.processing_fee_sgd;
            if(pm==='cash'&&pf!=null&&pf>0) return mkArg('rider_advocate','driver_fault','policy_inconsistent',`Cash + ${pf} SGD processing fee. FARE-11: cash has no processing fee.`,['FARE-11'],collectSids(pe,['FARE-11']),av,{policy_clarity:0.95,evidence_strength:0.90},'fee_reversal',w);
            const fr=f.fare_sgd, plf=f.platform_fee_sgd;
            if(fr!=null&&plf!=null){const exp=fr<=18?1.25:1.47;if(Math.abs(plf-exp)>0.01) return mkArg('rider_advocate','driver_fault','policy_inconsistent',`Fare ${fr} SGD, platform fee ${plf} SGD. Expected ${exp} (FARE-10).`,['FARE-10'],collectSids(pe,['FARE-10']),av,{policy_clarity:0.95,evidence_strength:0.90},'fee_correction',w);}
            return mkArg('rider_advocate','insufficient_evidence','insufficient_evidence','Insufficient fare data.',pids,collectSids(pe,pids),av,{policy_clarity:0.80,evidence_strength:0.30},null,w);
        }
        return mkArg('rider_advocate','insufficient_evidence','insufficient_evidence','No logic for this category.',[],[],av,{},null,['Not implemented.']);
    }
};

// --- Driver Advocate ---
const DriverAdvocate = {
    assess(pe,c) {
        const cat=c.category, f=c.facts, av=availEids(c);
        if(cat==='no_show_charge') {
            const pids=['CAN-02','CAN-09','CAN-10'], w=checkConf(pe,pids);
            const pa=f.pickup_arrival_verified, ws=f.wait_seconds, ch=f.rider_charge_sgd, dp=f.driver_payment_sgd;
            if(ch!=null&&dp!=null&&ch!==dp) w.push(`CAN-09: rider charge (${ch}) vs driver payment (${dp}) — different roles.`);
            if(pa===true&&ws!=null&&ws>180) return mkArg('driver_advocate','rider_fault','policy_consistent',`Driver arrived, waited ${ws}s (>180s, CAN-02). Charge consistent.`,pids,collectSids(pe,pids),av,{policy_clarity:0.90,evidence_strength:0.85},null,[...w,histNote(c)]);
            if(pa===false) return mkArg('driver_advocate','insufficient_evidence','policy_inconsistent','Driver arrival cannot be verified. CAN-02 requires verified arrival.',['CAN-02'],collectSids(pe,['CAN-02']),av,{policy_clarity:0.90,evidence_strength:0.40},null,w);
            return mkArg('driver_advocate','insufficient_evidence','insufficient_evidence','Missing arrival/wait data.',pids,collectSids(pe,pids),av,{policy_clarity:0.85,evidence_strength:0.30},null,w);
        }
        if(cat==='cancellation_fee') {
            const pids=['CAN-01','CAN-04','CAN-09'], w=checkConf(pe,pids);
            const mc=f.match_to_cancel_seconds, sb=f.seconds_before_schedule_at_cancel;
            if(mc!=null&&mc<=180) return mkArg('driver_advocate','no_fault','policy_inconsistent',`Cancel ${mc}s < 3-min grace (CAN-01). Inconsistent.`,['CAN-01'],collectSids(pe,['CAN-01']),av,{policy_clarity:0.95,evidence_strength:0.85},null,w);
            if(mc!=null&&mc>180) return mkArg('driver_advocate','rider_fault','policy_consistent',`Cancel ${mc}s > 3-min grace (CAN-01). Consistent.`,['CAN-01'],collectSids(pe,['CAN-01']),av,{policy_clarity:0.95,evidence_strength:0.85},null,w);
            if(sb!=null&&sb>900) return mkArg('driver_advocate','no_fault','policy_inconsistent',`Cancel ${sb}s >900s before pickup (CAN-04). Free.`,['CAN-04'],collectSids(pe,['CAN-04']),av,{policy_clarity:0.90,evidence_strength:0.80},null,w);
            return mkArg('driver_advocate','insufficient_evidence','insufficient_evidence','Missing timing data.',pids,collectSids(pe,pids),av,{policy_clarity:0.80,evidence_strength:0.30},null,w);
        }
        if(cat==='route_deviation') {
            const pids=['FARE-01','FARE-02'], w=checkConf(pe,pids);
            return mkArg('driver_advocate','no_fault','unsupported_rule','FARE-01 allows efficient GPS route. No public refund formula.',pids,collectSids(pe,pids),av,{policy_clarity:0.85,evidence_strength:0.65},null,w);
        }
        if(cat==='fare_dispute') {
            const pids=['FARE-02','FARE-10','FARE-11'], w=checkConf(pe,pids);
            const pm=f.payment, pf=f.processing_fee_sgd;
            if(pm==='cash'&&pf!=null&&pf>0) return mkArg('driver_advocate','driver_fault','policy_inconsistent',`Cash + ${pf} SGD processing fee. FARE-11: inconsistent.`,['FARE-11'],collectSids(pe,['FARE-11']),av,{policy_clarity:0.95,evidence_strength:0.90},null,w);
            return mkArg('driver_advocate','insufficient_evidence','insufficient_evidence','Insufficient fare data.',pids,collectSids(pe,pids),av,{policy_clarity:0.80,evidence_strength:0.30},null,w);
        }
        if(cat==='cleaning_fee') {
            const pids=['CLEAN-01','CLEAN-02','CLEAN-03','CLEAN-04'], w=checkConf(pe,pids);
            const ms=f.mess, co=f.verified_cleaning_cost_sgd, cd=f.professional_cleaning_delay_hours, rs=f.receipt_stamp_present;
            if(cd!=null&&cd>24) return mkArg('driver_advocate','insufficient_evidence','policy_inconsistent',`Cleaning delay ${cd}h > 24h (CLEAN-02).`,['CLEAN-02'],collectSids(pe,['CLEAN-02']),av,{policy_clarity:0.90,evidence_strength:0.70},null,w);
            if(rs===false) return mkArg('driver_advocate','insufficient_evidence','insufficient_evidence','No company stamp (CLEAN-03).',['CLEAN-03'],collectSids(pe,['CLEAN-03']),av,{policy_clarity:0.90,evidence_strength:0.50},null,w);
            if(ms&&co!=null){const params=pe.getRule('CLEAN-01')?.parameters||{};const caps={spillage:params.spillage_cap_sgd||40,bodily_fluid_stain:params.fluids_stains_cap_sgd||120,vomit:params.vomit_cap_sgd||200};const cap=caps[ms];if(cap&&co>cap) return mkArg('driver_advocate','no_fault','discretionary_review',`Cost ${co} > ${ms} cap ${cap} (CLEAN-01).`,['CLEAN-01'],collectSids(pe,['CLEAN-01']),av,{policy_clarity:0.85,evidence_strength:0.75},null,w);}
            const excl=['immediately_cleanable_mess','pet_fur','pet_saliva'];
            if(excl.includes(ms)) return mkArg('driver_advocate','no_fault','policy_inconsistent',`'${ms}' excluded (CLEAN-04).`,['CLEAN-04'],collectSids(pe,['CLEAN-04']),av,{policy_clarity:0.90,evidence_strength:0.80},null,w);
            return mkArg('driver_advocate','insufficient_evidence','insufficient_evidence','Insufficient cleaning data.',pids,collectSids(pe,pids),av,{policy_clarity:0.80,evidence_strength:0.30},null,w);
        }
        if(cat==='safety_incident') {
            const pids=['SAFE-01','SAFE-03','SAFE-07'];
            return mkArg('driver_advocate','insufficient_evidence','safety_escalation','Safety allegations require immediate human review. System escalates without inferring guilt.',pids,collectSids(pe,pids),av,{policy_clarity:0.95,evidence_strength:0.40},null,['SAFETY ESCALATION: Do not auto-resolve.']);
        }
        return mkArg('driver_advocate','insufficient_evidence','insufficient_evidence','No logic.',[],[],av,{},null,['Not implemented.']);
    }
};

// --- Judge Agent ---
const JudgeAgent = {
    assess(pe,c,ra,da) {
        if(ra.assessment==='safety_escalation'||da.assessment==='safety_escalation')
            return mkArg('judge','safety_escalation','safety_escalation','Safety allegation. Immediate human review.',[...new Set([...ra.policy_ids,...da.policy_ids])],[...new Set([...ra.source_ids,...da.source_ids])],[...new Set([...ra.evidence_ids,...da.evidence_ids])],{policy_clarity:0.95,evidence_strength:0.40},null,['SAFETY ESCALATION: Route to human review.']);
        if(ra.liability_label===da.liability_label&&ra.assessment===da.assessment) {
            let li=ra.liability_label, as=ra.assessment;
            if(as==='discretionary_review') li='discretionary_review';
            return mkArg('judge',li,as,`Consensus: Both advocates agree. ${ra.rationale} Liability: ${li}.`,[...new Set([...ra.policy_ids,...da.policy_ids])],[...new Set([...ra.source_ids,...da.source_ids])],[...new Set([...ra.evidence_ids,...da.evidence_ids])],{policy_clarity:0.90,evidence_strength:0.85,agent_consistency:0.95},null,[...new Set([...ra.warnings,...da.warnings]),histNote(c)]);
        }
        if(ra.assessment==='source_conflict'||da.assessment==='source_conflict')
            return mkArg('judge','source_conflict','source_conflict','Sources conflict. Route to human review.',[...new Set([...ra.policy_ids,...da.policy_ids])],[...new Set([...ra.source_ids,...da.source_ids])],[...new Set([...ra.evidence_ids,...da.evidence_ids])],{policy_clarity:0.40,evidence_strength:0.60},null,['Source conflict: human review.']);
        if(ra.assessment==='policy_gap'||da.assessment==='policy_gap')
            return mkArg('judge','policy_gap','policy_gap','Policy gap. Obtain clarification.',[...new Set([...ra.policy_ids,...da.policy_ids])],[...new Set([...ra.source_ids,...da.source_ids])],[...new Set([...ra.evidence_ids,...da.evidence_ids])],{policy_clarity:0.30,evidence_strength:0.60},null,['Policy gap: human review.']);
        if(ra.assessment==='insufficient_evidence'||da.assessment==='insufficient_evidence')
            return mkArg('judge','insufficient_evidence','insufficient_evidence','Insufficient evidence. Missing facts stay UNKNOWN.',[...new Set([...ra.policy_ids,...da.policy_ids])],[...new Set([...ra.source_ids,...da.source_ids])],[...new Set([...ra.evidence_ids,...da.evidence_ids])],{policy_clarity:0.70,evidence_strength:0.25},null,['Do not fabricate (BR-02).','Request additional evidence.']);
        return mkArg('judge','contested','conflicting_evidence','Advocates disagree. Re-evaluation or debate needed.',[...new Set([...ra.policy_ids,...da.policy_ids])],[...new Set([...ra.source_ids,...da.source_ids])],[...new Set([...ra.evidence_ids,...da.evidence_ids])],{policy_clarity:0.70,evidence_strength:0.50,agent_consistency:0.40},null,['Disagreement: trigger challenge gate.']);
    }
};

// --- Verification ---
function verify(pe,arg,evIds) {
    const checks=[], fails=[];
    checks.push('policy_ids_exist'); for(const p of arg.policy_ids) if(!pe.getRule(p)) fails.push(`Unknown policy: ${p}`);
    checks.push('evidence_ids_exist'); for(const e of arg.evidence_ids) if(!evIds.includes(e)) fails.push(`Unknown evidence: ${e}`);
    checks.push('source_ids_resolve'); const allSids=new Set(); for(const p of arg.policy_ids){const r=pe.getRule(p);if(r)r.source_ids.forEach(s=>allSids.add(s));} for(const s of arg.source_ids) if(!allSids.has(s)) fails.push(`Source ${s} not resolved`);
    checks.push('no_unauthorized_monetary'); if(arg.requested_remedy&&String(arg.requested_remedy).includes('cash_refund')) fails.push('Agent proposed cash_refund (BR-07)');
    checks.push('safety_escalation_enforced'); if(arg.assessment==='safety_escalation'&&!['safety_escalation','insufficient_evidence'].includes(arg.liability_label)) fails.push('Safety must escalate');
    return {passed:fails.length===0,checks_run:checks,failures:fails};
}

// --- Confidence ---
function computeConfidence(j,r,d) {
    const p=j.confidence_factors.policy_clarity||0.50, e=((r.confidence_factors.evidence_strength||0.50)+(d.confidence_factors.evidence_strength||0.50))/2, c=0.80, a=j.confidence_factors.agent_consistency||0.50, rr=j.confidence_factors.claim_reliability||0.50;
    const tot=CONFIDENCE_WEIGHTS.policy_clarity*p+CONFIDENCE_WEIGHTS.evidence_strength*e+CONFIDENCE_WEIGHTS.historical_consistency*c+CONFIDENCE_WEIGHTS.agent_consistency*a+CONFIDENCE_WEIGHTS.claim_reliability*rr;
    return {policy_clarity:+p.toFixed(3),evidence_strength:+e.toFixed(3),historical_consistency:+c.toFixed(3),agent_consistency:+a.toFixed(3),claim_reliability:+rr.toFixed(3),total:+tot.toFixed(3)};
}
function routeDest(conf,cat,vp,safety) {
    if(safety) return 'human_review'; if(!vp) return 'human_review';
    if(HIGH_RISK_CATEGORIES.includes(cat)&&conf.total<HIGH_CONF_THRESHOLD) return 'human_review';
    if(conf.total<LOW_CONF_THRESHOLD) return 'human_review';
    if(conf.total>=HIGH_CONF_THRESHOLD) return 'auto_resolve';
    return 'challenge_window';
}

// --- Refund Engine ---
function calcRefund(pe,cat,facts,liability) {
    if(['rider_fault','safety_escalation'].includes(liability)) return {amount_sgd:0.0,currency:'SGD',policy_id:'',calculation_basis:'Rider at fault or safety escalation — no refund.',capped:false,notes:['No refund.']};
    if(['insufficient_evidence','contested','source_conflict','policy_gap','discretionary_review'].includes(liability)) return {amount_sgd:0.0,currency:'SGD',policy_id:'',calculation_basis:'Insufficient evidence or human review.',capped:false,notes:['No auto-refund.']};
    if(cat==='no_show_charge'||cat==='cancellation_fee') {const ch=facts.rider_charge_sgd;if(ch==null) return {amount_sgd:0.0,currency:'SGD',policy_id:'CAN-07',calculation_basis:'No verified charge.',capped:false,notes:[]};const r=pe.getRule('CAN-07');const v=r?.parameters?.approved_voucher_sgd||6.61;return {amount_sgd:v,currency:'SGD',policy_id:'CAN-07',calculation_basis:`Charge ${ch} SGD. CAN-07: voucher ${v} SGD.`,capped:true,notes:['Voucher not cash.','Within 30 days.','Subject to approval.']};}
    if(cat==='waiting_fee') {const r=pe.getRule('CAN-08');const v=r?.parameters?.approved_voucher_sgd||5.0;return {amount_sgd:v,currency:'SGD',policy_id:'CAN-08',calculation_basis:`CAN-08: ${v} SGD voucher.`,capped:true,notes:['Voucher not cash.','Within 30 days.']};}
    if(cat==='cleaning_fee') {const r=pe.getRule('CLEAN-01');if(!r) return {amount_sgd:0.0,currency:'SGD',policy_id:'',calculation_basis:'',capped:false,notes:[]};const ms=facts.mess||'';const co=facts.verified_cleaning_cost_sgd||0;const caps={spillage:r.parameters.spillage_cap_sgd||40,bodily_fluid_stain:r.parameters.fluids_stains_cap_sgd||120,vomit:r.parameters.vomit_cap_sgd||200};const cap=caps[ms];if(cap==null) return {amount_sgd:0.0,currency:'SGD',policy_id:'CLEAN-01',calculation_basis:`Unknown mess: ${ms}.`,capped:false,notes:[]};const am=Math.min(co,cap);return {amount_sgd:am,currency:'SGD',policy_id:'CLEAN-01',calculation_basis:`Cost ${co}, cap ${cap}. min=${am}.`,capped:co>cap,notes:['Caps are ceilings.','Subject to review.']};}
    if(cat==='fare_dispute') {const qt=facts.quoted_fare_sgd,ch=facts.base_fare_charged_sgd;if(qt==null||ch==null) return {amount_sgd:0.0,currency:'SGD',policy_id:'FARE-02',calculation_basis:'Need quoted and charged.',capped:false,notes:[]};const ov=Math.max(ch-qt,0);return {amount_sgd:ov,currency:'SGD',policy_id:'FARE-02',calculation_basis:`Quoted ${qt}, charged ${ch}. Overcharge=${ov}.`,capped:false,notes:['Refund = verified overcharge.']};}
    return {amount_sgd:0.0,currency:'SGD',policy_id:'',calculation_basis:'No deterministic rule.',capped:false,notes:['Manual review.']};
}

// --- Dispute Resolver ---
function resolveDispute(pe,cse) {
    const now=new Date().toISOString();
    const result={dispute_id:cse.dispute_id,category:cse.category,timestamp:now,stages:[]};
    const policies=pe.getRulesForCategory(cse.category);
    result.stages.push({stage:'intake_triage',status:'completed',details:{category:cse.category,applicable_policies:policies.map(p=>p.policy_id),filed_by:cse.filed_by}});
    const evR=EvidenceCollector.validate(cse.evidence);Object.assign(cse.facts,EvidenceCollector.extractFacts(cse.evidence));
    result.stages.push({stage:'evidence_collection',status:'completed',details:evR});
    const rArg=RiderAdvocate.assess(pe,cse), dArg=DriverAdvocate.assess(pe,cse);
    result.rider_argument=rArg.toDict();result.driver_argument=dArg.toDict();
    result.stages.push({stage:'advocate_assessment',status:'completed',details:{rider_assessment:rArg.assessment,driver_assessment:dArg.assessment}});
    const evIds=cse.evidence.map(e=>e.evidence_id);const rV=verify(pe,rArg,evIds),dV=verify(pe,dArg,evIds);const vp=rV.passed&&dV.passed;
    result.stages.push({stage:'verification',status:'completed',details:{rider_verification:{passed:rV.passed,failures:rV.failures},driver_verification:{passed:dV.passed,failures:dV.failures}}});
    const jArg=JudgeAgent.assess(pe,cse,rArg,dArg);result.judge_ruling=jArg.toDict();
    result.stages.push({stage:'judge_ruling',status:'completed',details:{liability:jArg.liability_label,assessment:jArg.assessment}});
    const safety=rArg.assessment==='safety_escalation'||dArg.assessment==='safety_escalation';const conf=computeConfidence(jArg,rArg,dArg);const dest=routeDest(conf,cse.category,vp,safety);
    result.confidence_score=conf;result.route=dest;
    result.stages.push({stage:'confidence_routing',status:'completed',details:{confidence:conf,route:dest}});
    result.final_assessment=jArg.assessment;result.liability_label=jArg.liability_label;
    if(dest==='auto_resolve'){result.human_review_required=false;result.final_decision=true;result.next_step='Auto-resolved. Challenge window open for 48 hours.';result.refund=calcRefund(pe,cse.category,cse.facts,jArg.liability_label);}
    else if(dest==='challenge_window'){result.human_review_required=true;result.final_decision=false;result.next_step='Preliminary ruling issued. Challenge window open.';result.refund=calcRefund(pe,cse.category,cse.facts,jArg.liability_label);}
    else{result.human_review_required=true;result.final_decision=false;result.next_step=`Escalated to human review. ${safety?'Safety allegation requires immediate investigation. ':''}Evidence preserved for audit.`;}
    result.stages.push({stage:'final_decision',status:'completed',details:{final_assessment:result.final_assessment,liability_label:result.liability_label,human_review_required:result.human_review_required,final_decision:result.final_decision,refund:result.refund}});
    return result;
}

// --- Sample Cases ---
function mkEv(id,kind,status,field,value,supports,desc){return{evidence_id:id,kind,status,field:field||'',value,supports_fields:supports||[],source_description:desc||''};}
const DEMO_CASES={
    disp002:{dispute_id:'DISP-002',trip_id:'TRIP-2026-09945',filed_by:'rider',category:'no_show_charge',description:"I was at the pickup at Tiong Bahru Plaza on time but the driver never showed. The app charged me $5.00 for a 'no-show'.",filed_at:'2026-09-13T09:20:00+08:00',case_date:'2026-09-13',rider_id:'R-7823',driver_id:'D-2398',facts:{pickup_arrival_verified:true,wait_seconds:480,trip_completed:false,rider_absent:true,rider_charge_sgd:5.00,driver_payment_sgd:4.50,fee_type:'no_show',match_to_cancel_seconds:null,service:'on_demand'},evidence:[mkEv('E1','gps_telemetry','available','pickup_arrival_verified',true,['pickup_arrival_verified','wait_seconds'],'GPS: driver stationary 08:43-08:51'),mkEv('E2','gps_telemetry','available','wait_seconds',480,['wait_seconds'],'GPS: 8 min at pickup'),mkEv('E3','chat_log','available','driver_contact_attempts',5,['driver_contact_attempts'],'4 messages + 1 call'),mkEv('E4','payment_data','available','rider_charge_sgd',5.00,['rider_charge_sgd'],'$5.00 cancellation fee'),mkEv('E5','app_event','available','driver_arrival_time','2026-09-13T08:43:00+08:00',['pickup_arrival_verified'],'driver_arrived 08:43'),mkEv('E6','app_event','available','cancellation_time','2026-09-13T08:51:00+08:00',[],'cancelled 08:51 rider_no_show'),mkEv('E7','payment_data','available','driver_payment_sgd',4.50,['driver_payment_sgd'],'$4.50 driver payment')],prior_rejected_disputes:3,driver_rating:4.9},
    route_deviation:{dispute_id:'DISP-003',trip_id:'TRIP-2026-10067',filed_by:'rider',category:'route_deviation',description:'Driver took longer route from Tiong Bahru to VivoCity. Overcharged 25%. Want 20% refund.',filed_at:'2026-09-15T14:30:00+08:00',case_date:'2026-09-15',rider_id:'R-5432',driver_id:'D-1102',facts:{service:'RydeFLASH',quoted_fare_sgd:18,base_fare_charged_sgd:18,route_distance_increase_pct:25,requested_refund_pct:20},evidence:[mkEv('E1','payment_data','available','quoted_fare_sgd',18,[],'Quoted $18'),mkEv('E2','payment_data','available','base_fare_charged_sgd',18,[],'Charged $18'),mkEv('E3','gps_telemetry','available','route_distance_increase_pct',25,[],'GPS: 25% longer')],prior_rejected_disputes:0,driver_rating:4.7},
    cancellation_grace:{dispute_id:'DISP-004',trip_id:'TRIP-2026-10089',filed_by:'rider',category:'cancellation_fee',description:'Cancelled right after matching — wrong destination. Charged $6.61 but within 2 minutes.',filed_at:'2026-09-16T10:15:00+08:00',case_date:'2026-09-16',rider_id:'R-8890',driver_id:'D-3344',facts:{service:'RydeFLASH',match_to_cancel_seconds:120,rider_charge_sgd:6.61},evidence:[mkEv('E1','app_event','available','match_to_cancel_seconds',120,[],'Match 10:13, cancel 10:15 (120s)'),mkEv('E2','payment_data','available','rider_charge_sgd',6.61,[],'$6.61 fee')],prior_rejected_disputes:0,driver_rating:4.5},
    cash_fee:{dispute_id:'DISP-005',trip_id:'TRIP-2026-10112',filed_by:'rider',category:'fare_dispute',description:"Paid cash but there's a $0.60 processing fee on my receipt.",filed_at:'2026-09-17T16:00:00+08:00',case_date:'2026-09-17',rider_id:'R-2233',driver_id:'D-7788',facts:{payment:'cash',processing_fee_sgd:0.60,fare_sgd:15.00,platform_fee_sgd:1.25},evidence:[mkEv('E1','payment_data','available','payment','cash',[],'Payment: cash'),mkEv('E2','payment_data','available','processing_fee_sgd',0.60,[],'$0.60 processing fee')],prior_rejected_disputes:0,driver_rating:4.6},
    safety:{dispute_id:'DISP-006',trip_id:'TRIP-2026-10134',filed_by:'rider',category:'safety_incident',description:'Driver was driving dangerously and made inappropriate comments. I felt unsafe.',filed_at:'2026-09-18T20:30:00+08:00',case_date:'2026-09-18',rider_id:'R-4455',driver_id:'D-9911',facts:{harassment_allegation:true,message_record_present:true,responsibility_verified:false},evidence:[mkEv('E1','chat_log','available','harassment_allegation',true,[],'Inappropriate messages')],prior_rejected_disputes:0,driver_rating:4.2},
};

// Expose globally
window.RydeApp={PolicyEngine,resolveDispute,DEMO_CASES};
