import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const ChatInterface = ({ sessionId }) => {
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const [currentUploadType, setCurrentUploadType] = useState(null);
    const messagesEndRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        const welcomeMessage = {
            id: Date.now(),
            role: 'assistant',
            content: "Hi! I'm your Water Stewardship AI Assistant. I help you track water usage, assess risks, optimize efficiency, and ensure compliance. What would you like to do today?",
            options: [
                { id: 'upload', label: 'Upload Water Data', icon: '📤' },
                { id: 'dashboard', label: 'View Dashboard', icon: '📊' },
                { id: 'risk', label: 'Water Risk Assessment', icon: '🗺️' },
                { id: 'footprint', label: 'Calculate Water Footprint', icon: '💧' },
                { id: 'efficiency', label: 'Efficiency Opportunities', icon: '📈' },
                { id: 'compliance', label: 'Compliance & Permits', icon: '📋' },
                { id: 'supply_chain', label: 'Supply Chain Water Risk', icon: '🌊' },
                { id: 'strategy', label: 'Build Stewardship Strategy', icon: '🎯' },
                { id: 'ask', label: 'Ask Me Anything', icon: '💬' }
            ],
            timestamp: new Date()
        };
        setMessages([welcomeMessage]);
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSendMessage = async (text) => {
        if (!text.trim()) return;

        const userMessage = {
            id: Date.now(),
            role: 'user',
            content: text,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsTyping(true);

        try {
            const response = await axios.post(`${API_URL}/api/chat/message`, {
                session_id: sessionId,
                message: text
            });

            setIsTyping(false);

            console.log('Backend response:', response.data);

            // Normalize agent response (new shape) → legacy dashboard_data shape
            const agentData = response.data.data || null;
            let dashboard_data = response.data.dashboard_data || null;

            if (!dashboard_data && response.data.type === 'dashboard' && agentData) {
                const cards = agentData.summary_cards || [];
                const usageCard = cards.find(c => c.title?.includes('Usage') || c.title?.includes('Withdrawal'));
                const costCard = cards.find(c => c.title?.includes('Cost'));
                const facilityCard = cards.find(c => c.title?.includes('Facilit'));
                const complianceCard = cards.find(c => c.title?.includes('Compliance'));

                dashboard_data = {
                    total_usage: usageCard?.raw || agentData.total_usage || 0,
                    total_cost: costCard?.raw || agentData.total_cost || 0,
                    facilities: {
                        total: facilityCard?.raw || (agentData.facility_breakdown?.length ?? 0),
                        list: (agentData.facility_breakdown || []).map(f => ({
                            name: f.facility,
                            usage: f.volume_gallons,
                            cost: 0,
                        })),
                    },
                    compliance: {
                        rate: agentData.compliance?.rate ?? complianceCard?.raw ?? 100,
                        passed_tests: parseInt((agentData.compliance?.tests || '0/0').split('/')[0]) || 0,
                        total_tests: parseInt((agentData.compliance?.tests || '0/0').split('/')[1]) || 0,
                    },
                    insights: agentData.insights || [],
                    recommendations: agentData.recommendations || [],
                    avg_cost_per_1000_gal: agentData.avg_cost_per_1000_gal || 0,
                    meters: agentData.meters || {},
                    suppliers: agentData.suppliers || {},
                };
            }

            const assistantMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: response.data.content || 'I received your message!',
                options: response.data.options || null,
                showUpload: response.data.type === 'upload_prompt',
                uploadType: response.data.upload_type || null,
                dashboard_data,
                risk_data: response.data.risk_data || (response.data.type === 'risk_assessment' ? (() => {
                    const d = agentData;
                    if (!d) return null;
                    // Normalize agent field names → frontend expected names
                    return {
                        overall_risk: d.overall_risk_level || d.overall_risk,
                        risk_score: d.overall_portfolio_risk ?? d.overall_risk_score ?? d.risk_score,
                        facilities: (d.facilities || []).map(f => ({
                            ...f,
                            name: f.facility_name || f.name,
                            overall_risk: f.overall_risk_level || f.overall_risk,
                            risk_score: f.overall_risk_score ?? f.risk_score,
                            risk_breakdown: f.risk_breakdown || {},
                        })),
                        key_risks: d.key_risks || [],
                        recommendations: d.recommendations || [],
                    };
                })() : null),
                mitigation_plan: response.data.mitigation_plan || null,
                comparison_data: response.data.comparison_data || (response.data.type === 'facility_comparison' ? agentData : null),
                map_data: response.data.map_data || null,
                climate_data: response.data.climate_data || null,
                supplier_risk_data: response.data.supplier_risk_data || (response.data.type === 'suppliers' ? agentData : null),
                footprint_data: response.data.footprint_data || (response.data.type === 'water_footprint' ? response.data.data : null),
                industry_comparison_data: response.data.type === 'industry_comparison' ? response.data.data : null,
                reduction_targets_data: response.data.type === 'reduction_targets' ? response.data.data : null,
                footprint_hotspots_data: response.data.type === 'footprint_hotspots' ? response.data.data : null,
                footprint_report_data: response.data.type === 'footprint_report' ? response.data.data : null,
                engagement_plan: response.data.engagement_plan || null,
                compliance_data: response.data.type === 'compliance' ? agentData : null,
                dmr_data: response.data.type === 'dmr_report' ? response.data.dmr_data : null,
                efficiency_data: response.data.type === 'efficiency' ? agentData : null,
                strategy_data: response.data.type === 'stewardship_strategy' ? response.data.strategy_data : null,
                trends_data: response.data.type === 'trends' ? response.data.data : null,
                water_balance_data: response.data.type === 'water_balance' ? response.data.data : null,
                pollutant_data: response.data.type === 'pollutant_levels' ? response.data.data : null,
                cost_data: response.data.type === 'cost_analysis' ? response.data.data : null,
                facility_risk_comparison: response.data.type === 'facility_risk_comparison' ? response.data.data : null,
                risk_map_data: response.data.type === 'risk_map' ? response.data.data : null,
                climate_scenarios_data: response.data.type === 'climate_scenarios' ? response.data.data : null,
                timestamp: new Date()
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            setIsTyping(false);
            console.error('Error details:', error);
            console.error('Error response:', error.response?.data);

            const errorMessage = {
                id: Date.now() + 1,
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
        }
    };

    const handleOptionClick = (optionId) => {
        const option = messages[messages.length - 1]?.options?.find(o => o.id === optionId);

        // Route specific option IDs to guaranteed phrases that won't be misrouted
        const ID_TO_MESSAGE = {
            // Sidebar / welcome screen primary actions
            'upload': 'Upload Water Data',
            'dashboard': 'View Dashboard overview summary',
            'risk': 'Water Risk Assessment water stress',
            'footprint': 'Calculate Water Footprint',
            'efficiency': 'Efficiency Opportunities savings',
            'compliance': 'Compliance & Permits',
            'supply_chain': 'Supplier supply chain water risk',
            'ask': 'Ask Me Anything',
            // Secondary actions
            'supplier_risk': 'Assess Supplier Risks supply chain',
            'compare_facilities': 'Compare All Facilities side by side',
            'risk_map': 'View Risk Map facilities',
            'climate_scenarios': 'See Climate Scenarios projections',
            'mitigation': 'Get Risk Mitigation Strategies plan',
            'generate_dmr': 'Generate DMR Report discharge monitoring',
            'compare_industry': 'Compare to Industry benchmark',
            'set_reduction_target': 'Set Reduction Target water',
            'identify_hotspots': 'Identify Hotspots top usage',
            'generate_footprint_report': 'Generate footprint report download',
            'strategy': 'Build Stewardship Strategy',
        };
        if (ID_TO_MESSAGE[optionId]) {
            handleSendMessage(ID_TO_MESSAGE[optionId]);
            return;
        }

        // Handle download plan
        if (optionId === 'download_plan') {
            // Search backwards through messages to find the plan
            let planMessage = null;
            for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].mitigation_plan || messages[i].engagement_plan) {
                    planMessage = messages[i];
                    break;
                }
            }
            let planHTML;
            let filename;

            if (planMessage?.engagement_plan) {
                planHTML = generateEngagementPlanHTML(planMessage.engagement_plan);
                filename = 'Supplier_Engagement_Plan_2026.html';
            } else if (planMessage?.mitigation_plan) {
                planHTML = generateMitigationPlanHTML(planMessage.mitigation_plan);
                filename = 'Water_Risk_Mitigation_Plan_2026.html';
            } else {
                planHTML = generateMitigationPlanHTML();
                filename = 'Water_Plan_2026.html';
            }

            const blob = new Blob([planHTML], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            // Show confirmation message
            const confirmMsg = {
                id: Date.now(),
                role: 'assistant',
                content: '✅ Plan downloaded successfully! You can open the HTML file in your browser and print it as PDF (Ctrl+P or Cmd+P).',
                timestamp: new Date()
            };
            setMessages(prev => [...prev, confirmMsg]);
            return;
        }

        // Handle dashboard view switch
        if (optionId === 'show_dashboard') {
            // Send message to backend
            handleSendMessage('Yes, Show Dashboard');
            // Notify parent to switch view (if needed in future)
            return;
        }

        // Track upload type based on option clicked
        if (optionId === 'utility_bills') {
            setCurrentUploadType('utility_bill');
        } else if (optionId === 'meter_readings') {
            setCurrentUploadType('meter_data');
        } else if (optionId === 'facility_info') {
            setCurrentUploadType('facility_info');
        } else if (optionId === 'supplier_list') {
            setCurrentUploadType('supplier_list');
        } else if (optionId === 'discharge_reports') {
            setCurrentUploadType('discharge_report');
        }

        // Check if this is an upload file action
        if (optionId === 'upload_file') {
            // Show file upload interface
            const uploadMessage = {
                id: Date.now(),
                role: 'assistant',
                content: 'Please select a file to upload:',
                showUpload: true,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, uploadMessage]);
            return;
        }

        if (optionId === 'download_strategy') {
            let stratMsg = null;
            for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].strategy_data) { stratMsg = messages[i]; break; }
            }
            const s = stratMsg?.strategy_data || {};
            const prioritiesHTML = (s.priorities || []).map(p => `
              <div class="priority-card">
                <div class="priority-rank">#${p.rank}</div>
                <div class="priority-body">
                  <div class="priority-title">${p.title}</div>
                  <div class="priority-desc">${p.description}</div>
                  <div class="priority-meta"><span class="tag-impact">${p.impact}</span><span class="tag-time">${p.timeline}</span></div>
                </div>
              </div>`).join('');
            const kpisHTML = (s.kpis || []).map(k => `
              <tr><td>${k.metric}</td><td>${k.baseline}</td><td class="target">${k.target}</td><td>${k.frequency}</td></tr>`).join('');
            const timelineHTML = (s.timeline || []).map(t => `
              <div class="phase-card">
                <div class="phase-header">${t.phase} <span class="phase-period">${t.period}</span></div>
                ${(t.actions || []).map(a => `<div class="phase-action">• ${a}</div>`).join('')}
              </div>`).join('');
            const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Water Stewardship Strategy</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#f5f7fa;padding:40px 20px;color:#1f2937}
.container{max-width:960px;margin:0 auto;background:white;padding:48px;box-shadow:0 4px 24px rgba(0,0,0,.08);border-radius:12px}
.header{border-bottom:3px solid #2563eb;padding-bottom:16px;margin-bottom:8px}
h1{color:#1e40af;font-size:28px;font-weight:700}
.subtitle{color:#6b7280;font-size:13px;margin-top:4px}
.target-banner{display:flex;gap:16px;margin:24px 0;padding:20px;background:linear-gradient(135deg,#eff6ff,#dbeafe);border-radius:10px;border:1px solid #bfdbfe}
.target-item{flex:1;text-align:center}
.target-label{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.target-value{font-size:22px;font-weight:700;color:#1e40af}
.summary{padding:16px 20px;background:#f9fafb;border-left:4px solid #2563eb;border-radius:0 8px 8px 0;margin-bottom:28px;font-size:14px;line-height:1.7;color:#374151}
h2{font-size:17px;font-weight:700;color:#1f2937;margin:28px 0 14px;display:flex;align-items:center;gap:8px}
h2::before{content:'';display:inline-block;width:4px;height:18px;background:#2563eb;border-radius:2px}
.priority-card{display:flex;gap:14px;padding:14px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;margin-bottom:10px}
.priority-rank{width:32px;height:32px;background:#2563eb;color:white;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0}
.priority-title{font-size:14px;font-weight:600;color:#1f2937;margin-bottom:4px}
.priority-desc{font-size:12px;color:#6b7280;margin-bottom:8px}
.priority-meta{display:flex;gap:8px;flex-wrap:wrap}
.tag-impact{padding:3px 10px;background:#d1fae5;color:#065f46;border-radius:12px;font-size:11px;font-weight:600}
.tag-time{padding:3px 10px;background:#dbeafe;color:#1e40af;border-radius:12px;font-size:11px;font-weight:600}
table{width:100%;border-collapse:collapse;font-size:13px}
thead tr{background:#f3f4f6}
th{padding:10px 12px;text-align:left;font-weight:600;color:#374151;border-bottom:2px solid #e5e7eb}
td{padding:10px 12px;border-bottom:1px solid #f3f4f6;color:#1f2937}
.target{color:#059669;font-weight:600}
.timeline-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.phase-card{padding:14px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb}
.phase-header{font-size:13px;font-weight:700;color:#1e40af;margin-bottom:8px}
.phase-period{font-size:11px;color:#6b7280;font-weight:400;margin-left:6px}
.phase-action{font-size:12px;color:#374151;padding:3px 0}
.footer{margin-top:32px;padding-top:16px;border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af;text-align:center}
@media print{body{padding:0}.container{box-shadow:none;border-radius:0}}
</style></head><body><div class="container">
<div class="header">
  <h1>💧 Water Stewardship Strategy</h1>
  <div class="subtitle">Generated ${s.generated_date || new Date().toISOString().slice(0, 10)} · Confidential</div>
</div>
<div class="target-banner">
  <div class="target-item"><div class="target-label">Reduction Target</div><div class="target-value">${s.target_reduction_pct || 30}%</div></div>
  <div class="target-item"><div class="target-label">Target Year</div><div class="target-value">${s.target_year || 2027}</div></div>
  <div class="target-item"><div class="target-label">Current Usage</div><div class="target-value">${((s.total_gal || 0) / 1000000).toFixed(2)}M gal</div></div>
  <div class="target-item"><div class="target-label">Annual Cost</div><div class="target-value">$${((s.total_cost || 0) / 1000).toFixed(0)}K</div></div>
</div>
<div class="summary">${s.executive_summary || ''}</div>
<h2>Strategic Priorities</h2>
${prioritiesHTML}
<h2>Key Performance Indicators</h2>
<table><thead><tr><th>Metric</th><th>Baseline</th><th>Target</th><th>Review Frequency</th></tr></thead><tbody>${kpisHTML}</tbody></table>
<h2>Implementation Timeline</h2>
<div class="timeline-grid">${timelineHTML}</div>
<div class="footer">Water Stewardship Strategy · ${s.generated_date || new Date().toISOString().slice(0, 10)} · For internal use only</div>
</div></body></html>`;
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = 'Water_Stewardship_Strategy.html';
            document.body.appendChild(a); a.click();
            document.body.removeChild(a); URL.revokeObjectURL(url);
            setMessages(prev => [...prev, { id: Date.now(), role: 'assistant', content: '✅ Strategy downloaded! Open in browser and print as PDF (Ctrl+P).', timestamp: new Date() }]);
            return;
        }

        if (optionId === 'download_dmr') {
            let dmrMsg = null;
            for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].dmr_data) { dmrMsg = messages[i]; break; }
            }
            const d = dmrMsg?.dmr_data || {};
            const permitsHTML = (d.permits || []).map(p => `
                <div class="permit">
                    <div class="permit-header">
                        <div>
                            <div class="permit-id">${p.permit_id}</div>
                            <div class="permit-meta">${p.permit_type} · ${p.issuing_authority} · Outfall: ${p.outfall_id}</div>
                        </div>
                        <div class="status-badge ${p.overall_status === 'Compliant' ? 'compliant' : 'violation'}">${p.overall_status}</div>
                    </div>
                    <div class="permit-stats">
                        <div class="stat"><div class="stat-label">Discharge Volume</div><div class="stat-value">${(p.discharge_volume_gallons || 0).toLocaleString()} gal</div></div>
                        <div class="stat"><div class="stat-label">Avg Daily Flow</div><div class="stat-value">${(p.avg_daily_flow_gallons || 0).toLocaleString()} gal/day</div></div>
                        <div class="stat"><div class="stat-label">Compliance Rate</div><div class="stat-value">${p.compliance_rate}%</div></div>
                        <div class="stat"><div class="stat-label">Lab</div><div class="stat-value">${p.lab_name}</div></div>
                    </div>
                    <table class="params-table">
                        <thead><tr><th>Parameter</th><th>Average</th><th>Maximum</th><th>Limit</th><th>Unit</th><th>Status</th></tr></thead>
                        <tbody>
                            ${(p.parameters || []).map(param => `
                            <tr>
                                <td>${param.name}</td>
                                <td>${param.average_value}</td>
                                <td>${param.max_value}</td>
                                <td>${param.limit}</td>
                                <td>${param.unit}</td>
                                <td class="${param.status === 'pass' ? 'pass' : 'fail'}">${param.status === 'pass' ? '✅ Pass' : '❌ Fail'}</td>
                            </tr>`).join('')}
                        </tbody>
                    </table>
                </div>`).join('');

            const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>${d.report_title || 'DMR Report'}</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#f5f5f5;padding:40px 20px}
.container{max-width:960px;margin:0 auto;background:white;padding:40px;box-shadow:0 2px 10px rgba(0,0,0,.1)}
h1{color:#1d4ed8;font-size:28px;border-bottom:3px solid #1d4ed8;padding-bottom:10px;margin-bottom:6px}
.subtitle{color:#6b7280;font-size:13px;margin-bottom:24px}
h2{color:#1f2937;font-size:18px;margin:28px 0 12px;border-bottom:1px solid #e5e7eb;padding-bottom:6px}
.permit{margin-bottom:32px;padding:20px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb}
.permit-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px}
.permit-id{font-size:16px;font-weight:700;color:#1d4ed8}
.permit-meta{font-size:12px;color:#6b7280;margin-top:4px}
.status-badge{padding:6px 14px;border-radius:6px;font-size:12px;font-weight:700}
.compliant{background:#d1fae5;color:#065f46}
.violation{background:#fee2e2;color:#991b1b}
.permit-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.stat{padding:10px;background:white;border-radius:6px;border:1px solid #e5e7eb}
.stat-label{font-size:10px;color:#6b7280;margin-bottom:4px}
.stat-value{font-size:14px;font-weight:600;color:#1f2937}
.params-table{width:100%;border-collapse:collapse;font-size:13px}
.params-table th{padding:8px 10px;background:#f3f4f6;color:#374151;text-align:left;font-weight:600}
.params-table td{padding:8px 10px;border-bottom:1px solid #f3f4f6;color:#1f2937}
.pass{color:#065f46;font-weight:600}
.fail{color:#991b1b;font-weight:600}
.certification{margin-top:32px;padding:16px;background:#eff6ff;border-left:4px solid #1d4ed8;font-size:12px;color:#374151;font-style:italic}
@media print{body{padding:0}.container{box-shadow:none}}
</style></head><body><div class="container">
<h1>${d.report_title || 'Discharge Monitoring Report'}</h1>
<div class="subtitle">Reporting Period: ${d.reporting_period || '—'} · Generated: ${d.generated_date || new Date().toISOString().slice(0, 10)}</div>
<h2>Permit Results</h2>
${permitsHTML}
${d.recommendations?.length ? `<h2>Recommendations</h2><ul style="padding-left:20px;font-size:13px;color:#374151">${d.recommendations.map(r => `<li style="margin-bottom:6px">${r}</li>`).join('')}</ul>` : ''}
<div class="certification">${d.certification || ''}</div>
</div></body></html>`;

            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = 'DMR_Report.html';
            document.body.appendChild(a); a.click();
            document.body.removeChild(a); URL.revokeObjectURL(url);
            setMessages(prev => [...prev, { id: Date.now(), role: 'assistant', content: '✅ DMR Report downloaded! Open in browser and print as PDF (Ctrl+P).', timestamp: new Date() }]);
            return;
        }

        if (optionId === 'download_footprint_report') {
            let reportMsg = null;
            for (let i = messages.length - 1; i >= 0; i--) {
                if (messages[i].footprint_report_data) { reportMsg = messages[i]; break; }
            }
            const d = reportMsg?.footprint_report_data;
            const fp = d?.footprint || {};
            const ind = d?.industry || {};
            const hs = d?.hotspots || {};
            const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Water Footprint Report</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:#f5f5f5;padding:40px 20px}.container{max-width:900px;margin:0 auto;background:white;padding:40px;box-shadow:0 2px 10px rgba(0,0,0,.1)}h1{color:#2563eb;font-size:28px;border-bottom:3px solid #2563eb;padding-bottom:10px;margin-bottom:20px}h2{color:#1f2937;font-size:20px;margin:30px 0 12px;border-bottom:1px solid #e5e7eb;padding-bottom:6px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:16px 0}.card{padding:16px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb}.card-label{font-size:11px;color:#6b7280;margin-bottom:4px}.card-value{font-size:20px;font-weight:700;color:#1f2937}.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f3f4f6;font-size:13px}.row-label{color:#6b7280}.row-value{font-weight:600;color:#1f2937}@media print{body{padding:0}.container{box-shadow:none}}</style>
</head><body><div class="container">
<h1>💧 Water Footprint Report</h1>
<p style="color:#6b7280;margin-bottom:24px">Generated ${new Date().toISOString().slice(0, 10)}</p>
<h2>Direct Footprint</h2>
<div class="grid">
  <div class="card"><div class="card-label">Total Withdrawal</div><div class="card-value">${((fp.direct?.total_withdrawal_gallons || 0) / 1000).toFixed(0)}K gal</div></div>
  <div class="card"><div class="card-label">Consumed</div><div class="card-value">${((fp.direct?.consumption_gallons || 0) / 1000).toFixed(0)}K gal</div></div>
  <div class="card"><div class="card-label">Discharged</div><div class="card-value">${((fp.direct?.discharge_gallons || 0) / 1000).toFixed(0)}K gal</div></div>
  <div class="card"><div class="card-label">Grey Water</div><div class="card-value">${((fp.direct?.grey_water_gallons || 0) / 1000).toFixed(0)}K gal</div></div>
</div>
<h2>Industry Comparison</h2>
<div class="grid">
  <div class="card"><div class="card-label">Your Intensity</div><div class="card-value">${(ind.your_intensity || 0).toLocaleString()} gal/$1M</div></div>
  <div class="card"><div class="card-label">Industry Average</div><div class="card-value">${(ind.industry_average || 0).toLocaleString()} gal/$1M</div></div>
  <div class="card"><div class="card-label">Best-in-Class</div><div class="card-value">${(ind.best_in_class || 0).toLocaleString()} gal/$1M</div></div>
  <div class="card"><div class="card-label">vs Average</div><div class="card-value" style="color:${(ind.vs_average_pct || 0) > 0 ? '#ef4444' : '#10b981'}">${(ind.vs_average_pct || 0) > 0 ? '+' : ''}${ind.vs_average_pct || 0}%</div></div>
</div>
<h2>Top Hotspots</h2>
${(hs.by_facility || []).map(f => `<div class="row"><span class="row-label">${f.facility}</span><span class="row-value">${(f.gallons / 1000).toFixed(0)}K gal (${f.percentage}%)</span></div>`).join('')}
<h2>Supply Chain</h2>
<div class="row"><span class="row-label">Total Supply Chain</span><span class="row-value">${((fp.supply_chain?.total_gallons || 0) / 1000).toFixed(0)}K gal</span></div>
${(fp.supply_chain?.breakdown || []).map(s => `<div class="row"><span class="row-label">${s.supplier} (${s.category})</span><span class="row-value">${(s.footprint_gallons / 1000).toFixed(0)}K gal</span></div>`).join('')}
</div></body></html>`;
            const blob = new Blob([html], { type: 'text/html' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = 'Water_Footprint_Report.html';
            document.body.appendChild(a); a.click();
            document.body.removeChild(a); URL.revokeObjectURL(url);
            setMessages(prev => [...prev, { id: Date.now(), role: 'assistant', content: '✅ Footprint report downloaded! Open in browser and print as PDF.', timestamp: new Date() }]);
            return;
        }

        if (option) {
            handleSendMessage(option.label);
        }
    };

    const generateMitigationPlanHTML = (plan) => {
        const p = plan || {};
        const fmt = (n) => Number(n || 0).toLocaleString('en-US');
        const phasesHTML = (p.phases || []).map(phase => `
        <div class="phase">
            <div class="phase-header">
                <div>
                    <div class="phase-title">Phase ${phase.phase}: ${phase.name}</div>
                    <div class="phase-duration">${phase.duration}</div>
                </div>
                <div class="phase-status" style="${phase.status === 'ready' ? 'background:#d1fae5;color:#065f46' : 'background:#fef3c7;color:#78350f'}">${(phase.status || 'pending').toUpperCase()}</div>
            </div>
            ${(phase.actions || []).map(a => `
            <div class="action">
                <div>
                    <div class="action-task">${a.task}</div>
                    <div class="action-meta">Owner: ${a.owner} | Due: ${a.deadline}</div>
                </div>
                <div class="action-cost">$${fmt(a.cost)}</div>
            </div>`).join('')}
        </div>`).join('');

        const kpisHTML = (p.kpis || []).map(kpi => `
        <div class="kpi-card">
            <div class="kpi-metric">${kpi.metric}</div>
            <div class="kpi-values">Baseline: ${kpi.baseline}</div>
            <div class="kpi-values">Target: ${kpi.target}</div>
            <div class="kpi-change">${kpi.reduction ? '↓ ' + kpi.reduction : kpi.increase ? '↑ ' + kpi.increase : 'Maintain'}</div>
        </div>`).join('');

        const risksHTML = (p.risk_mitigation || []).map(r => `
        <div class="risk-item">
            <div class="risk-header">
                <span class="risk-impact" style="${r.impact === 'High' ? 'background:#fca5a5;color:#7f1d1d' : 'background:#fbbf24;color:#78350f'}">${(r.impact || '').toUpperCase()}</span>
                <span class="risk-text">${r.risk} → ${r.mitigation}</span>
            </div>
            <div class="risk-timeline">Timeline: ${r.timeline}</div>
        </div>`).join('');

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${p.plan_name || 'Water Risk Mitigation Plan'}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 40px 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #10b981; font-size: 32px; margin-bottom: 10px; border-bottom: 3px solid #10b981; padding-bottom: 10px; }
        .header-info { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }
        .info-card { padding: 15px; background: #f9fafb; border-left: 4px solid #10b981; }
        .info-label { font-size: 12px; color: #6b7280; text-transform: uppercase; margin-bottom: 5px; }
        .info-value { font-size: 18px; font-weight: 600; color: #1f2937; }
        h2 { color: #1f2937; font-size: 24px; margin: 30px 0 15px; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; }
        .phase { margin-bottom: 30px; padding: 20px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; }
        .phase-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .phase-title { font-size: 18px; font-weight: 600; color: #2563eb; }
        .phase-duration { font-size: 14px; color: #6b7280; }
        .phase-status { padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; text-transform: uppercase; }
        .action { padding: 12px; background: white; border-left: 3px solid #2563eb; margin-bottom: 10px; display: flex; justify-content: space-between; }
        .action-task { font-size: 14px; color: #1f2937; margin-bottom: 4px; }
        .action-meta { font-size: 12px; color: #6b7280; }
        .action-cost { font-size: 14px; font-weight: 600; color: #f59e0b; white-space: nowrap; margin-left: 16px; }
        .kpi-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }
        .kpi-card { padding: 15px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; }
        .kpi-metric { font-size: 14px; color: #6b7280; margin-bottom: 8px; }
        .kpi-values { font-size: 13px; color: #1f2937; margin-bottom: 4px; }
        .kpi-change { font-size: 14px; font-weight: 600; color: #10b981; }
        .risk-item { padding: 12px; background: #fef3c7; border-left: 4px solid #f59e0b; margin-bottom: 10px; }
        .risk-header { display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }
        .risk-impact { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
        .risk-text { font-size: 13px; color: #1f2937; }
        .risk-timeline { font-size: 12px; color: #6b7280; margin-top: 4px; }
        @media print { body { padding: 0; } .container { box-shadow: none; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>${p.plan_name || 'Water Risk Mitigation Strategy'}</h1>
        <p style="color:#6b7280;margin-bottom:20px;">Generated on ${p.created_date || new Date().toISOString().slice(0, 10)}</p>
        <div class="header-info">
            <div class="info-card"><div class="info-label">Timeline</div><div class="info-value">${p.timeline || '—'}</div></div>
            <div class="info-card"><div class="info-label">Total Investment</div><div class="info-value" style="color:#ef4444;">$${fmt(p.total_investment)}</div></div>
            <div class="info-card"><div class="info-label">Expected Savings</div><div class="info-value" style="color:#10b981;">$${fmt(p.expected_savings)}/yr</div></div>
            <div class="info-card"><div class="info-label">ROI Period</div><div class="info-value" style="color:#2563eb;">${p.roi_months || '—'} months</div></div>
        </div>
        <h2>Implementation Phases</h2>
        ${phasesHTML || '<p style="color:#6b7280">No phases defined.</p>'}
        <h2>Key Performance Indicators</h2>
        <div class="kpi-grid">${kpisHTML || '<p style="color:#6b7280">No KPIs defined.</p>'}</div>
        <h2>Risk Mitigation Actions</h2>
        ${risksHTML || '<p style="color:#6b7280">No risk actions defined.</p>'}
    </div>
</body>
</html>`;
    };

    const generateEngagementPlanHTML = (plan) => {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${plan.plan_name}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 40px 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #2563eb; font-size: 32px; margin-bottom: 10px; border-bottom: 3px solid #2563eb; padding-bottom: 10px; }
        .header-info { padding: 15px; background: #eff6ff; border-left: 4px solid #2563eb; margin: 20px 0; }
        h2 { color: #1f2937; font-size: 24px; margin: 30px 0 15px; border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; }
        .tier { margin-bottom: 30px; padding: 20px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; }
        .tier-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .tier-title { font-size: 18px; font-weight: 600; }
        .tier1 { color: #dc2626; }
        .tier2 { color: #f59e0b; }
        .tier3 { color: #10b981; }
        .tier-badge { padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; }
        .badge-tier1 { background: #fee2e2; color: #dc2626; }
        .badge-tier2 { background: #fef3c7; color: #f59e0b; }
        .badge-tier3 { background: #d1fae5; color: #10b981; }
        .suppliers { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
        .supplier-tag { padding: 4px 10px; background: #e5e7eb; border-radius: 4px; font-size: 11px; }
        .action { padding: 10px; background: white; border-left: 3px solid #2563eb; margin-bottom: 8px; }
        .action-text { font-size: 13px; color: #1f2937; margin-bottom: 4px; }
        .action-meta { font-size: 11px; color: #6b7280; }
        .goals { padding: 10px; background: white; border-radius: 6px; margin-top: 10px; }
        .goal-item { font-size: 12px; color: #1f2937; margin-bottom: 4px; }
        .timeline-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin: 20px 0; }
        .timeline-card { padding: 15px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; }
        .timeline-title { font-size: 13px; font-weight: 600; color: #2563eb; margin-bottom: 8px; }
        .timeline-item { font-size: 12px; color: #1f2937; margin-bottom: 4px; }
        .kpi-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 20px 0; }
        .kpi-card { padding: 15px; background: #f9fafb; border-radius: 8px; border: 1px solid #e5e7eb; }
        .kpi-metric { font-size: 13px; color: #1f2937; margin-bottom: 6px; }
        .kpi-target { font-size: 14px; font-weight: 600; color: #10b981; }
        .resource-item { padding: 12px; background: #f9fafb; border-radius: 6px; margin-bottom: 10px; display: flex; justify-content: space-between; }
        .resource-name { font-size: 13px; font-weight: 600; color: #1f2937; }
        .resource-cost { font-size: 13px; font-weight: 600; color: #f59e0b; }
        .resource-desc { font-size: 11px; color: #6b7280; margin-top: 4px; }
        @media print { body { padding: 0; } .container { box-shadow: none; } }
    </style>
</head>
<body>
    <div class="container">
        <h1>${plan.plan_name}</h1>
        <p style="color: #6b7280; margin-bottom: 20px;">Generated on ${plan.created_date}</p>
        
        <div class="header-info">
            <strong>Strategy Overview:</strong> Tiered approach to engage ${plan.total_suppliers} suppliers based on water risk and spend
        </div>

        <h2>Engagement Tiers</h2>
        
        ${plan.tiers.map(tier => `
        <div class="tier">
            <div class="tier-header">
                <div>
                    <div class="tier-title tier${tier.tier}">Tier ${tier.tier}: ${tier.name}</div>
                    <div style="font-size: 11px; color: #6b7280; margin-top: 4px;">${tier.criteria}</div>
                </div>
                <div class="tier-badge badge-tier${tier.tier}">${tier.supplier_count} Suppliers</div>
            </div>
            
            ${tier.suppliers.length > 0 ? `
            <div style="margin-bottom: 12px;">
                <div style="font-size: 11px; color: #6b7280; margin-bottom: 6px; font-weight: 600;">Suppliers:</div>
                <div class="suppliers">
                    ${tier.suppliers.map(s => `<span class="supplier-tag">${s.name}</span>`).join('')}
                </div>
            </div>
            ` : ''}
            
            <div style="margin-bottom: 12px;">
                <div style="font-size: 11px; color: #6b7280; margin-bottom: 6px; font-weight: 600;">Actions:</div>
                ${tier.actions.map(action => `
                <div class="action">
                    <div class="action-text">${action.action}</div>
                    <div class="action-meta">${action.timeline} | ${action.owner}</div>
                </div>
                `).join('')}
            </div>
            
            <div class="goals">
                <div style="font-size: 11px; color: #6b7280; margin-bottom: 6px; font-weight: 600;">Goals:</div>
                ${Object.entries(tier.goals).map(([key, value]) => `
                <div class="goal-item">• ${key.replace(/_/g, ' ')}: ${value}</div>
                `).join('')}
            </div>
        </div>
        `).join('')}

        <h2>2026 Implementation Timeline</h2>
        <div class="timeline-grid">
            ${Object.entries(plan.timeline).map(([quarter, activities]) => `
            <div class="timeline-card">
                <div class="timeline-title">${quarter.replace('_', ' ').toUpperCase()}</div>
                ${activities.map(activity => `<div class="timeline-item">• ${activity}</div>`).join('')}
            </div>
            `).join('')}
        </div>

        <h2>Key Performance Indicators</h2>
        <div class="kpi-grid">
            ${plan.kpis.map(kpi => `
            <div class="kpi-card">
                <div class="kpi-metric">${kpi.metric}</div>
                <div class="kpi-target">Target: ${kpi.target}</div>
            </div>
            `).join('')}
        </div>

        <h2>Required Resources</h2>
        ${plan.resources.map(resource => `
        <div class="resource-item">
            <div>
                <div class="resource-name">${resource.resource}</div>
                <div class="resource-desc">${resource.description}</div>
            </div>
            <div class="resource-cost">${resource.cost}</div>
        </div>
        `).join('')}
    </div>
</body>
</html>`;
    };

    const SIDEBAR_ITEMS = [
        { id: 'upload', label: 'Upload Water Data', icon: '📤' },
        { id: 'dashboard', label: 'View Dashboard', icon: '📊' },
        { id: 'risk', label: 'Water Risk Assessment', icon: '🗺️' },
        { id: 'footprint', label: 'Calculate Water Footprint', icon: '💧' },
        { id: 'efficiency', label: 'Efficiency Opportunities', icon: '📈' },
        { id: 'compliance', label: 'Compliance & Permits', icon: '📋' },
        { id: 'supply_chain', label: 'Supply Chain Water Risk', icon: '🌊' },
        { id: 'strategy', label: 'Build Stewardship Strategy', icon: '🎯' },
        { id: 'ask', label: 'Ask Me Anything', icon: '💬' },
    ];

    return (
        <div className="app-layout">
            <div className="chat-container">
                <header className="chat-header">
                    <h1>Water Stewardship Agent</h1>
                </header>
                <div className="chat-messages">
                    {messages.map((message) => (
                        <div key={message.id} className={`message-wrapper ${message.role}`}>
                            <div className={`message-avatar ${message.role === 'user' ? 'user' : 'bot'}`}>
                                {message.role === 'user' ? '👤' : '💧'}
                            </div>
                            <div className="message-content">
                                <div className={`message-bubble ${message.role === 'user' ? 'user' : 'bot'}`}>
                                    {message.content}
                                </div>

                                {message.showUpload && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <input
                                            type="file"
                                            accept=".pdf,.csv,.xlsx,.xls"
                                            onChange={async (e) => {
                                                if (e.target.files[0]) {
                                                    const file = e.target.files[0];

                                                    // Show uploading message
                                                    const uploadingMsg = {
                                                        id: Date.now(),
                                                        role: 'assistant',
                                                        content: `📤 Uploading "${file.name}"... Processing with AI to extract water data...`,
                                                        timestamp: new Date()
                                                    };
                                                    setMessages(prev => [...prev, uploadingMsg]);

                                                    // Upload file to backend
                                                    try {
                                                        const formData = new FormData();
                                                        formData.append('file', file);
                                                        formData.append('file_type', message.uploadType || currentUploadType || 'utility_bill');
                                                        formData.append('user_id', 'demo');

                                                        const response = await axios.post(`${API_URL}/api/upload/`, formData, {
                                                            headers: { 'Content-Type': 'multipart/form-data' }
                                                        });

                                                        // Show extracted data
                                                        const extractedData = response.data.extracted_data || {};
                                                        const dataDisplay = Object.entries(extractedData)
                                                            .map(([key, value]) => `• ${key.replace(/_/g, ' ')}: ${JSON.stringify(value)}`)
                                                            .join('\n');

                                                        const successMsg = {
                                                            id: Date.now() + 1,
                                                            role: 'assistant',
                                                            content: `✅ Processing... Done! I extracted:\n\n${dataDisplay}`,
                                                            extractedData: extractedData,
                                                            options: [
                                                                { id: 'upload', label: '📤 Upload Another File', icon: '📤' },
                                                                { id: 'dashboard', label: '📊 View Dashboard', icon: '📊' },
                                                                { id: 'risk', label: '🗺️ Water Risk Assessment', icon: '🗺️' },
                                                                { id: 'efficiency', label: '📈 Efficiency Opportunities', icon: '📈' },
                                                            ],
                                                            timestamp: new Date()
                                                        };
                                                        setMessages(prev => [...prev, successMsg]);

                                                    } catch (error) {
                                                        console.error('Upload error:', error);
                                                        const errorMsg = {
                                                            id: Date.now() + 1,
                                                            role: 'assistant',
                                                            content: `❌ Upload failed. ${error.response?.data?.detail || 'Please try again.'}`,
                                                            timestamp: new Date()
                                                        };
                                                        setMessages(prev => [...prev, errorMsg]);
                                                    }
                                                }
                                            }}
                                            style={{
                                                width: '100%',
                                                padding: '12px',
                                                background: '#3a3a3a',
                                                border: '1px solid #4a4a4a',
                                                borderRadius: '6px',
                                                color: '#ffffff',
                                                cursor: 'pointer'
                                            }}
                                        />
                                        <p style={{ marginTop: '8px', fontSize: '12px', color: '#9ca3af' }}>
                                            Accepted: PDF, CSV, Excel (Max 10MB)
                                        </p>
                                    </div>
                                )}

                                {message.mitigation_plan && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        {/* Plan Header */}
                                        <div style={{ padding: '16px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #10b981', marginBottom: '20px' }}>
                                            <div style={{ fontSize: '16px', fontWeight: '700', color: '#10b981', marginBottom: '8px' }}>
                                                {message.mitigation_plan.plan_name}
                                            </div>
                                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginTop: '12px' }}>
                                                <div>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af' }}>Timeline</div>
                                                    <div style={{ fontSize: '13px', fontWeight: '600', color: '#ffffff' }}>{message.mitigation_plan.timeline}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af' }}>Investment</div>
                                                    <div style={{ fontSize: '13px', fontWeight: '600', color: '#ef4444' }}>${Number(message.mitigation_plan.total_investment).toLocaleString('en-US')}</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af' }}>Expected Savings</div>
                                                    <div style={{ fontSize: '13px', fontWeight: '600', color: '#10b981' }}>${Number(message.mitigation_plan.expected_savings).toLocaleString('en-US')}/yr</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af' }}>ROI Period</div>
                                                    <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa' }}>{message.mitigation_plan.roi_months} months</div>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Implementation Phases */}
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                            Implementation Phases
                                        </h4>
                                        {message.mitigation_plan.phases.map((phase, idx) => (
                                            <div key={idx} style={{ marginBottom: '16px', padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                                    <div>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa' }}>
                                                            Phase {phase.phase}: {phase.name}
                                                        </div>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                                                            {phase.duration}
                                                        </div>
                                                    </div>
                                                    <div style={{
                                                        padding: '4px 10px',
                                                        borderRadius: '4px',
                                                        background: phase.status === 'ready' ? '#14532d' : '#78350f',
                                                        border: `1px solid ${phase.status === 'ready' ? '#10b981' : '#f59e0b'}`,
                                                        fontSize: '10px',
                                                        fontWeight: '600',
                                                        color: phase.status === 'ready' ? '#10b981' : '#f59e0b',
                                                        textTransform: 'uppercase'
                                                    }}>
                                                        {phase.status}
                                                    </div>
                                                </div>

                                                {/* Actions */}
                                                <div style={{ display: 'grid', gap: '8px' }}>
                                                    {phase.actions.map((action, aidx) => (
                                                        <div key={aidx} style={{ padding: '10px', background: '#2a2a2a', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                            <div style={{ flex: 1 }}>
                                                                <div style={{ fontSize: '12px', color: '#ffffff', marginBottom: '2px' }}>
                                                                    {action.task}
                                                                </div>
                                                                <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                                                                    Owner: {action.owner} | Due: {action.deadline}
                                                                </div>
                                                            </div>
                                                            <div style={{ fontSize: '11px', fontWeight: '600', color: '#f59e0b', whiteSpace: 'nowrap', marginLeft: '12px' }}>
                                                                ${Number(action.cost).toLocaleString('en-US')}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}

                                        {/* KPIs */}
                                        <div style={{ marginTop: '20px', marginBottom: '20px' }}>
                                            <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                Key Performance Indicators
                                            </h4>
                                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px' }}>
                                                {message.mitigation_plan.kpis.map((kpi, idx) => (
                                                    <div key={idx} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '6px' }}>
                                                            {kpi.metric}
                                                        </div>
                                                        <div style={{ fontSize: '12px', color: '#ffffff', marginBottom: '4px' }}>
                                                            <span style={{ color: '#9ca3af' }}>Baseline:</span> {kpi.baseline}
                                                        </div>
                                                        <div style={{ fontSize: '12px', color: '#ffffff', marginBottom: '4px' }}>
                                                            <span style={{ color: '#9ca3af' }}>Target:</span> {kpi.target}
                                                        </div>
                                                        <div style={{ fontSize: '12px', fontWeight: '600', color: kpi.maintain ? '#60a5fa' : '#10b981' }}>
                                                            {kpi.maintain ? 'Maintain' : kpi.reduction ? `↓ ${kpi.reduction}` : `↑ ${kpi.increase}`}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Risk Mitigation */}
                                        <div>
                                            <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                Risk Mitigation Actions
                                            </h4>
                                            <div style={{ display: 'grid', gap: '10px' }}>
                                                {message.mitigation_plan.risk_mitigation.map((item, idx) => (
                                                    <div key={idx} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a', display: 'flex', alignItems: 'center', gap: '12px' }}>
                                                        <div style={{
                                                            padding: '6px 10px',
                                                            borderRadius: '4px',
                                                            background: item.impact === 'High' ? '#7f1d1d' : '#78350f',
                                                            border: `1px solid ${item.impact === 'High' ? '#ef4444' : '#f59e0b'}`,
                                                            fontSize: '10px',
                                                            fontWeight: '600',
                                                            color: item.impact === 'High' ? '#ef4444' : '#f59e0b',
                                                            whiteSpace: 'nowrap'
                                                        }}>
                                                            {item.impact}
                                                        </div>
                                                        <div style={{ flex: 1 }}>
                                                            <div style={{ fontSize: '12px', color: '#ffffff', marginBottom: '2px' }}>
                                                                {item.risk} → {item.mitigation}
                                                            </div>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                                                                Timeline: {item.timeline}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {message.risk_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        {/* Overall Risk Score */}
                                        <div style={{ padding: '16px', background: '#1a1a1a', borderRadius: '8px', border: '2px solid #f59e0b', marginBottom: '20px', textAlign: 'center' }}>
                                            <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '8px' }}>Overall Water Risk</div>
                                            <div style={{ fontSize: '32px', fontWeight: '700', color: '#f59e0b', marginBottom: '4px' }}>
                                                {message.risk_data.overall_risk}
                                            </div>
                                            <div style={{ fontSize: '14px', color: '#9ca3af' }}>Risk Score: {message.risk_data.risk_score}/5.0</div>
                                        </div>

                                        {/* Facility Risk Breakdown */}
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                            Risk by Facility
                                        </h4>
                                        {message.risk_data.facilities.map((facility, idx) => (
                                            <div key={idx} style={{ marginBottom: '16px', padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                                    <div>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa' }}>
                                                            {facility.name}
                                                        </div>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                                                            {facility.location}
                                                        </div>
                                                    </div>
                                                    <div style={{
                                                        padding: '6px 12px',
                                                        borderRadius: '6px',
                                                        background: facility.risk_score >= 4 ? '#7f1d1d' : facility.risk_score >= 3 ? '#78350f' : facility.risk_score >= 2 ? '#713f12' : '#14532d',
                                                        border: `1px solid ${facility.risk_score >= 4 ? '#ef4444' : facility.risk_score >= 3 ? '#f59e0b' : facility.risk_score >= 2 ? '#fbbf24' : '#10b981'}`
                                                    }}>
                                                        <div style={{ fontSize: '11px', fontWeight: '600', color: facility.risk_score >= 4 ? '#ef4444' : facility.risk_score >= 3 ? '#f59e0b' : facility.risk_score >= 2 ? '#fbbf24' : '#10b981' }}>
                                                            {facility.overall_risk}
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Risk Parameters */}
                                                <div style={{ display: 'grid', gap: '8px' }}>
                                                    {Object.entries(facility.risk_breakdown).map(([key, risk]) => (
                                                        <div key={key} style={{ padding: '8px', background: '#2a2a2a', borderRadius: '4px' }}>
                                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                                                <span style={{ fontSize: '11px', color: '#ffffff', textTransform: 'capitalize' }}>
                                                                    {key.replace(/_/g, ' ')}
                                                                </span>
                                                                <span style={{
                                                                    fontSize: '10px',
                                                                    fontWeight: '600',
                                                                    color: risk.score >= 4 ? '#ef4444' : risk.score >= 3 ? '#f59e0b' : risk.score >= 2 ? '#fbbf24' : '#10b981'
                                                                }}>
                                                                    {risk.level}
                                                                </span>
                                                            </div>
                                                            <div style={{ width: '100%', height: '6px', background: '#3a3a3a', borderRadius: '3px', overflow: 'hidden' }}>
                                                                <div style={{
                                                                    width: `${(risk.score / 5) * 100}%`,
                                                                    height: '100%',
                                                                    background: risk.score >= 4 ? '#ef4444' : risk.score >= 3 ? '#f59e0b' : risk.score >= 2 ? '#fbbf24' : '#10b981',
                                                                    transition: 'width 0.3s'
                                                                }}></div>
                                                            </div>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '2px' }}>
                                                                {risk.description}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}

                                        {/* Key Risks */}
                                        <div style={{ marginTop: '20px', marginBottom: '20px' }}>
                                            <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                Key Risk Alerts
                                            </h4>
                                            {message.risk_data.key_risks.map((risk, idx) => (
                                                <div key={idx} style={{
                                                    padding: '12px',
                                                    background: '#1a1a1a',
                                                    borderRadius: '6px',
                                                    border: `1px solid ${risk.type === 'critical' ? '#ef4444' : risk.type === 'warning' ? '#f59e0b' : '#3a3a3a'}`,
                                                    marginBottom: '8px'
                                                }}>
                                                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                                                        <span style={{ fontSize: '16px' }}>
                                                            {risk.type === 'critical' ? '🚨' : risk.type === 'warning' ? '⚠️' : 'ℹ️'}
                                                        </span>
                                                        <div style={{ flex: 1 }}>
                                                            <div style={{ fontSize: '12px', color: '#ffffff', marginBottom: '4px' }}>
                                                                {risk.message}
                                                            </div>
                                                            <div style={{ fontSize: '11px', color: '#10b981' }}>
                                                                → {risk.action}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Recommendations */}
                                        <div>
                                            <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                Mitigation Recommendations
                                                <span style={{ fontSize: '10px', padding: '2px 8px', background: '#7c3aed', color: '#fff', borderRadius: '10px', fontWeight: '500' }}>✨ AI Generated</span>
                                            </h4>
                                            <div style={{ display: 'grid', gap: '10px' }}>
                                                {message.risk_data.recommendations.map((rec, idx) => (
                                                    <div key={idx} style={{
                                                        padding: '12px',
                                                        background: '#1a1a1a',
                                                        borderRadius: '6px',
                                                        border: '1px solid #3a3a3a',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '12px'
                                                    }}>
                                                        <div style={{
                                                            padding: '6px 10px',
                                                            borderRadius: '4px',
                                                            background: rec.priority === 'High' ? '#7f1d1d' : '#78350f',
                                                            border: `1px solid ${rec.priority === 'High' ? '#ef4444' : '#f59e0b'}`,
                                                            fontSize: '10px',
                                                            fontWeight: '600',
                                                            color: rec.priority === 'High' ? '#ef4444' : '#f59e0b',
                                                            whiteSpace: 'nowrap'
                                                        }}>
                                                            {rec.priority}
                                                        </div>
                                                        <div style={{ flex: 1 }}>
                                                            <div style={{ fontSize: '12px', color: '#ffffff', marginBottom: '2px' }}>
                                                                {rec.action}
                                                            </div>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                                                                Impact: {rec.impact}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {message.comparison_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>
                                            Facility Comparison
                                        </h4>

                                        {/* Comparison Table */}
                                        <div style={{ overflowX: 'auto', marginBottom: '20px' }}>
                                            <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                                                <thead>
                                                    <tr style={{ borderBottom: '2px solid #3a3a3a' }}>
                                                        <th style={{ padding: '10px', textAlign: 'left', color: '#9ca3af' }}>Metric</th>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <th key={idx} style={{ padding: '10px', textAlign: 'right', color: '#60a5fa' }}>
                                                                {facility.name}
                                                            </th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                        <td style={{ padding: '10px', color: '#9ca3af' }}>Location</td>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <td key={idx} style={{ padding: '10px', textAlign: 'right', color: '#ffffff', fontSize: '11px' }}>
                                                                {facility.location}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                    <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                        <td style={{ padding: '10px', color: '#9ca3af' }}>Water Usage</td>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <td key={idx} style={{ padding: '10px', textAlign: 'right', color: '#ffffff', fontWeight: '600' }}>
                                                                {facility.usage_gal_month.toLocaleString()} gal
                                                            </td>
                                                        ))}
                                                    </tr>
                                                    <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                        <td style={{ padding: '10px', color: '#9ca3af' }}>Monthly Cost</td>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <td key={idx} style={{ padding: '10px', textAlign: 'right', color: '#10b981', fontWeight: '600' }}>
                                                                ${facility.cost_month.toLocaleString()}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                    <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                        <td style={{ padding: '10px', color: '#9ca3af' }}>Cost per 1,000 gal</td>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <td key={idx} style={{ padding: '10px', textAlign: 'right', color: '#ffffff' }}>
                                                                ${facility.cost_per_1000_gal.toFixed(2)}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                    <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                        <td style={{ padding: '10px', color: '#9ca3af' }}>Employees</td>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <td key={idx} style={{ padding: '10px', textAlign: 'right', color: '#ffffff' }}>
                                                                {facility.employees}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                    <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                        <td style={{ padding: '10px', color: '#9ca3af' }}>Usage per Employee</td>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <td key={idx} style={{ padding: '10px', textAlign: 'right', color: '#ffffff' }}>
                                                                {facility.usage_per_employee.toLocaleString()} gal
                                                            </td>
                                                        ))}
                                                    </tr>
                                                    <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                        <td style={{ padding: '10px', color: '#9ca3af' }}>Risk Score</td>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <td key={idx} style={{ padding: '10px', textAlign: 'right', fontWeight: '600', color: facility.risk_score >= 3.5 ? '#ef4444' : facility.risk_score >= 2.5 ? '#f59e0b' : '#10b981' }}>
                                                                {facility.risk_score}/5.0
                                                            </td>
                                                        ))}
                                                    </tr>
                                                    <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                        <td style={{ padding: '10px', color: '#9ca3af' }}>Risk Level</td>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <td key={idx} style={{ padding: '10px', textAlign: 'right', fontWeight: '600', color: facility.risk_score >= 3.5 ? '#ef4444' : facility.risk_score >= 2.5 ? '#f59e0b' : '#10b981' }}>
                                                                {facility.risk_level}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                    <tr>
                                                        <td style={{ padding: '10px', color: '#9ca3af' }}>Efficiency Rating</td>
                                                        {message.comparison_data.facilities.map((facility, idx) => (
                                                            <td key={idx} style={{ padding: '10px', textAlign: 'right', fontWeight: '600', color: facility.efficiency_rating === 'Good' ? '#10b981' : facility.efficiency_rating === 'Fair' ? '#f59e0b' : '#ef4444' }}>
                                                                {facility.efficiency_rating}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>

                                        {/* Insights */}
                                        <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>
                                            Key Insights
                                        </h4>
                                        {message.comparison_data.comparison_insights.map((insight, idx) => (
                                            <div key={idx} style={{
                                                padding: '10px',
                                                background: '#1a1a1a',
                                                borderRadius: '6px',
                                                border: `1px solid ${insight.type === 'critical' ? '#ef4444' : insight.type === 'warning' ? '#f59e0b' : '#3a3a3a'}`,
                                                marginBottom: '8px',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '8px'
                                            }}>
                                                <span style={{ fontSize: '14px' }}>
                                                    {insight.type === 'critical' ? '🚨' : insight.type === 'warning' ? '⚠️' : 'ℹ️'}
                                                </span>
                                                <span style={{ fontSize: '11px', color: '#ffffff' }}>{insight.message}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {message.map_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>
                                            Water Risk Map
                                        </h4>

                                        {/* Map Legend */}
                                        <div style={{ marginBottom: '16px', padding: '12px', background: '#1a1a1a', borderRadius: '6px' }}>
                                            <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px', fontWeight: '600' }}>Risk Level Legend:</div>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                                                {message.map_data.legend.map((item, idx) => (
                                                    <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                                        <div style={{ width: '16px', height: '16px', borderRadius: '50%', background: item.color, border: '1px solid #3a3a3a' }}></div>
                                                        <span style={{ fontSize: '10px', color: '#ffffff' }}>{item.level} ({item.range})</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Facility Pins */}
                                        <div style={{ display: 'grid', gap: '12px' }}>
                                            {message.map_data.facilities.map((facility, idx) => (
                                                <div key={idx} style={{ padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: `2px solid ${facility.color}` }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                                        <div>
                                                            <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa' }}>
                                                                📍 {facility.name}
                                                            </div>
                                                            <div style={{ fontSize: '11px', color: '#9ca3af' }}>
                                                                {facility.location}
                                                            </div>
                                                        </div>
                                                        <div style={{
                                                            padding: '6px 12px',
                                                            borderRadius: '6px',
                                                            background: facility.risk_score >= 3.5 ? '#7f1d1d' : facility.risk_score >= 2.5 ? '#78350f' : '#14532d',
                                                            border: `1px solid ${facility.color}`
                                                        }}>
                                                            <div style={{ fontSize: '11px', fontWeight: '600', color: facility.color }}>
                                                                {facility.risk_level}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', fontSize: '11px' }}>
                                                        <div>
                                                            <span style={{ color: '#9ca3af' }}>Risk Score:</span>
                                                            <span style={{ color: '#ffffff', fontWeight: '600', marginLeft: '4px' }}>{facility.risk_score}/5.0</span>
                                                        </div>
                                                        <div>
                                                            <span style={{ color: '#9ca3af' }}>Usage:</span>
                                                            <span style={{ color: '#ffffff', fontWeight: '600', marginLeft: '4px' }}>{facility.usage_gal_month.toLocaleString()} gal</span>
                                                        </div>
                                                        <div style={{ gridColumn: 'span 2' }}>
                                                            <span style={{ color: '#9ca3af' }}>Coordinates:</span>
                                                            <span style={{ color: '#ffffff', marginLeft: '4px' }}>{facility.coordinates.lat.toFixed(4)}°N, {facility.coordinates.lon.toFixed(4)}°W</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {message.climate_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>
                                            Climate Scenarios (2030, 2040, 2050)
                                        </h4>

                                        {/* Scenarios */}
                                        {message.climate_data.scenarios.map((scenario, idx) => (
                                            <div key={idx} style={{ marginBottom: '20px' }}>
                                                <div style={{ fontSize: '13px', fontWeight: '600', color: '#f59e0b', marginBottom: '12px', padding: '8px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #f59e0b' }}>
                                                    📈 Projections for {scenario.year}
                                                </div>

                                                {scenario.facilities.map((facility, fidx) => (
                                                    <div key={fidx} style={{ marginBottom: '12px', padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ fontSize: '12px', fontWeight: '600', color: '#60a5fa', marginBottom: '8px' }}>
                                                            {facility.name} - {facility.location}
                                                        </div>

                                                        {/* Risk Progression */}
                                                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                                                            <div style={{ flex: 1 }}>
                                                                <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>Risk Progression</div>
                                                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                                    <span style={{ fontSize: '11px', color: '#10b981', fontWeight: '600' }}>
                                                                        Current: {facility.current_risk}
                                                                    </span>
                                                                    <span style={{ color: '#9ca3af' }}>→</span>
                                                                    <span style={{ fontSize: '11px', color: facility.projected_risk >= 4.5 ? '#ef4444' : facility.projected_risk >= 3.5 ? '#f59e0b' : '#fbbf24', fontWeight: '600' }}>
                                                                        {scenario.year}: {facility.projected_risk}
                                                                    </span>
                                                                    <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: '#7f1d1d', color: '#ef4444', fontWeight: '600' }}>
                                                                        {facility.change}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        {/* Key Changes */}
                                                        <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>Key Changes:</div>
                                                        <div style={{ display: 'grid', gap: '4px' }}>
                                                            {facility.key_changes.map((change, cidx) => (
                                                                <div key={cidx} style={{ fontSize: '10px', color: '#ffffff', paddingLeft: '8px' }}>
                                                                    • {change}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        ))}

                                        {/* Recommendations */}
                                        <div style={{ marginTop: '20px' }}>
                                            <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>
                                                Recommended Actions
                                            </h4>
                                            <div style={{ display: 'grid', gap: '10px' }}>
                                                {message.climate_data.recommendations.map((rec, idx) => (
                                                    <div key={idx} style={{
                                                        padding: '12px',
                                                        background: '#1a1a1a',
                                                        borderRadius: '6px',
                                                        border: '1px solid #3a3a3a',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '12px'
                                                    }}>
                                                        <div style={{
                                                            padding: '6px 10px',
                                                            borderRadius: '4px',
                                                            background: rec.priority === 'Critical' ? '#7f1d1d' : rec.priority === 'High' ? '#78350f' : '#713f12',
                                                            border: `1px solid ${rec.priority === 'Critical' ? '#ef4444' : rec.priority === 'High' ? '#f59e0b' : '#fbbf24'}`,
                                                            fontSize: '10px',
                                                            fontWeight: '600',
                                                            color: rec.priority === 'Critical' ? '#ef4444' : rec.priority === 'High' ? '#f59e0b' : '#fbbf24',
                                                            whiteSpace: 'nowrap'
                                                        }}>
                                                            {rec.priority}
                                                        </div>
                                                        <div style={{ flex: 1 }}>
                                                            <div style={{ fontSize: '11px', color: '#ffffff', marginBottom: '2px' }}>
                                                                {rec.action}
                                                            </div>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                                                                Timeline: {rec.timeline}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {message.supplier_risk_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>
                                            Supply Chain Water Risk Analysis
                                        </h4>

                                        {/* Summary Cards */}
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                                            <div style={{ padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>Total Suppliers</div>
                                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#60a5fa' }}>
                                                    {message.supplier_risk_data.total_suppliers}
                                                </div>
                                            </div>
                                            <div style={{ padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #ef4444' }}>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>High Risk</div>
                                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#ef4444' }}>
                                                    {message.supplier_risk_data.high_risk_count}
                                                </div>
                                                <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                                                    {message.supplier_risk_data.high_risk_percentage}% of total
                                                </div>
                                            </div>
                                            <div style={{ padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #f59e0b' }}>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>Medium Risk</div>
                                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#f59e0b' }}>
                                                    {message.supplier_risk_data.medium_risk_count}
                                                </div>
                                            </div>
                                            <div style={{ padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #10b981' }}>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>Low Risk</div>
                                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#10b981' }}>
                                                    {message.supplier_risk_data.low_risk_count}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Key Insights */}
                                        <div style={{ marginBottom: '20px' }}>
                                            <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>
                                                Key Insights
                                            </h4>
                                            {message.supplier_risk_data.key_insights.map((insight, idx) => (
                                                <div key={idx} style={{
                                                    padding: '10px',
                                                    background: '#1a1a1a',
                                                    borderRadius: '6px',
                                                    border: `1px solid ${insight.type === 'critical' ? '#ef4444' : insight.type === 'warning' ? '#f59e0b' : '#3a3a3a'}`,
                                                    marginBottom: '8px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '8px'
                                                }}>
                                                    <span style={{ fontSize: '14px' }}>
                                                        {insight.type === 'critical' ? '🚨' : insight.type === 'warning' ? '⚠️' : 'ℹ️'}
                                                    </span>
                                                    <span style={{ fontSize: '11px', color: '#ffffff' }}>{insight.message}</span>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Top Risk Suppliers */}
                                        <div style={{ marginBottom: '20px' }}>
                                            <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>
                                                Top Risk Suppliers
                                            </h4>
                                            {message.supplier_risk_data.top_risk_suppliers.map((supplier, idx) => (
                                                <div key={idx} style={{ marginBottom: '12px', padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: `1px solid ${supplier.water_intensity_factor > 200000 ? '#ef4444' : '#f59e0b'}` }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                                                        <div style={{ fontSize: '12px', fontWeight: '600', color: '#60a5fa' }}>
                                                            {supplier.supplier_name}
                                                        </div>
                                                        <div style={{
                                                            padding: '4px 8px',
                                                            borderRadius: '4px',
                                                            background: supplier.water_intensity_factor > 200000 ? '#7f1d1d' : '#78350f',
                                                            border: `1px solid ${supplier.water_intensity_factor > 200000 ? '#ef4444' : '#f59e0b'}`,
                                                            fontSize: '10px',
                                                            fontWeight: '600',
                                                            color: supplier.water_intensity_factor > 200000 ? '#ef4444' : '#f59e0b'
                                                        }}>
                                                            {supplier.water_intensity_factor > 200000 ? 'HIGH RISK' : 'MEDIUM RISK'}
                                                        </div>
                                                    </div>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '6px' }}>
                                                        {supplier.material_category} | {supplier.location.city}, {supplier.location.country}
                                                    </div>
                                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', fontSize: '11px' }}>
                                                        <div>
                                                            <span style={{ color: '#9ca3af' }}>Annual Spend:</span>
                                                            <span style={{ color: '#ffffff', fontWeight: '600', marginLeft: '4px' }}>
                                                                ${supplier.annual_spend_usd.toLocaleString()}
                                                            </span>
                                                        </div>
                                                        <div>
                                                            <span style={{ color: '#9ca3af' }}>Water Intensity:</span>
                                                            <span style={{ color: supplier.water_intensity_factor > 200000 ? '#ef4444' : '#f59e0b', fontWeight: '600', marginLeft: '4px' }}>
                                                                {supplier.water_intensity_factor.toLocaleString()}
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Recommendations */}
                                        <div>
                                            <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                Recommended Actions
                                                <span style={{ fontSize: '10px', padding: '2px 8px', background: '#7c3aed', color: '#fff', borderRadius: '10px', fontWeight: '500' }}>✨ AI Generated</span>
                                            </h4>
                                            <div style={{ display: 'grid', gap: '10px' }}>
                                                {message.supplier_risk_data.recommendations.map((rec, idx) => (
                                                    <div key={idx} style={{
                                                        padding: '12px',
                                                        background: '#1a1a1a',
                                                        borderRadius: '6px',
                                                        border: '1px solid #3a3a3a',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '12px'
                                                    }}>
                                                        <div style={{
                                                            padding: '6px 10px',
                                                            borderRadius: '4px',
                                                            background: rec.priority === 'High' ? '#7f1d1d' : '#78350f',
                                                            border: `1px solid ${rec.priority === 'High' ? '#ef4444' : '#f59e0b'}`,
                                                            fontSize: '10px',
                                                            fontWeight: '600',
                                                            color: rec.priority === 'High' ? '#ef4444' : '#f59e0b',
                                                            whiteSpace: 'nowrap'
                                                        }}>
                                                            {rec.priority}
                                                        </div>
                                                        <div style={{ flex: 1 }}>
                                                            <div style={{ fontSize: '11px', color: '#ffffff', marginBottom: '2px' }}>
                                                                {rec.action}
                                                            </div>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                                                                Impact: {rec.impact}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {message.footprint_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>
                                            💧 Water Footprint Analysis
                                        </h4>

                                        {!message.footprint_data.has_data ? (
                                            <div style={{ color: '#9ca3af', fontSize: '13px' }}>No water data found. Upload utility bills and meter data first.</div>
                                        ) : (
                                            <>
                                                {/* Total Footprint Card */}
                                                <div style={{ padding: '20px', background: '#1a1a1a', borderRadius: '8px', border: '2px solid #60a5fa', marginBottom: '20px', textAlign: 'center' }}>
                                                    <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '8px' }}>Total Water Footprint</div>
                                                    <div style={{ fontSize: '36px', fontWeight: '700', color: '#60a5fa', marginBottom: '8px' }}>
                                                        {message.footprint_data.total_footprint_gallons >= 1000000
                                                            ? `${(message.footprint_data.total_footprint_gallons / 1000000).toFixed(2)}M`
                                                            : `${(message.footprint_data.total_footprint_gallons / 1000).toFixed(0)}K`}
                                                    </div>
                                                    <div style={{ fontSize: '13px', color: '#9ca3af' }}>gallons</div>
                                                </div>

                                                {/* Direct vs Supply Chain */}
                                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '20px' }}>
                                                    <div style={{ padding: '16px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #10b981' }}>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '6px' }}>Direct (Operational)</div>
                                                        <div style={{ fontSize: '22px', fontWeight: '700', color: '#10b981', marginBottom: '4px' }}>
                                                            {message.footprint_data.direct.total_withdrawal_gallons >= 1000000
                                                                ? `${(message.footprint_data.direct.total_withdrawal_gallons / 1000000).toFixed(2)}M`
                                                                : `${(message.footprint_data.direct.total_withdrawal_gallons / 1000).toFixed(0)}K`} gal
                                                        </div>
                                                        <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                                                            Consumed: {(message.footprint_data.direct.consumption_rate_pct || 0).toFixed(1)}%
                                                        </div>
                                                    </div>
                                                    <div style={{ padding: '16px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #f59e0b' }}>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '6px' }}>Supply Chain</div>
                                                        <div style={{ fontSize: '22px', fontWeight: '700', color: '#f59e0b', marginBottom: '4px' }}>
                                                            {message.footprint_data.supply_chain.total_gallons >= 1000000
                                                                ? `${(message.footprint_data.supply_chain.total_gallons / 1000000).toFixed(2)}M`
                                                                : `${(message.footprint_data.supply_chain.total_gallons / 1000).toFixed(0)}K`} gal
                                                        </div>
                                                        <div style={{ fontSize: '10px', color: '#9ca3af' }}>
                                                            {message.footprint_data.supply_chain.breakdown?.length || 0} suppliers
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Blue / Grey / Consumption / Discharge */}
                                                <div style={{ marginBottom: '20px' }}>
                                                    <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>Direct Breakdown</h4>
                                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                                                        {[
                                                            { label: 'Blue Water (Withdrawal)', val: message.footprint_data.direct.blue_water_gallons, color: '#60a5fa' },
                                                            { label: 'Grey Water (Pollution)', val: message.footprint_data.direct.grey_water_gallons, color: '#9ca3af' },
                                                            { label: 'Consumed', val: message.footprint_data.direct.consumption_gallons, color: '#f59e0b' },
                                                            { label: 'Discharged', val: message.footprint_data.direct.discharge_gallons, color: '#10b981' },
                                                        ].map((item, i) => (
                                                            <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                                <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>{item.label}</div>
                                                                <div style={{ fontSize: '14px', fontWeight: '600', color: item.color }}>
                                                                    {item.val >= 1000000
                                                                        ? `${(item.val / 1000000).toFixed(2)}M`
                                                                        : `${(item.val / 1000).toFixed(0)}K`} gal
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>

                                                {/* By Facility */}
                                                {message.footprint_data.by_facility?.length > 0 && (
                                                    <div style={{ marginBottom: '20px' }}>
                                                        <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>By Facility</h4>
                                                        {message.footprint_data.by_facility.map((f, idx) => (
                                                            <div key={idx} style={{ marginBottom: '8px' }}>
                                                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '11px' }}>
                                                                    <span style={{ color: '#ffffff' }}>{f.facility}</span>
                                                                    <span style={{ color: '#9ca3af' }}>{(f.gallons / 1000).toFixed(0)}K gal ({f.percentage}%)</span>
                                                                </div>
                                                                <div style={{ width: '100%', height: '6px', background: '#3a3a3a', borderRadius: '3px', overflow: 'hidden' }}>
                                                                    <div style={{ width: `${f.percentage}%`, height: '100%', background: idx === 0 ? '#60a5fa' : idx === 1 ? '#f59e0b' : '#10b981', transition: 'width 0.3s' }} />
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* By Source */}
                                                {message.footprint_data.by_source?.length > 0 && (
                                                    <div style={{ marginBottom: '20px' }}>
                                                        <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#ffffff' }}>By Source</h4>
                                                        {message.footprint_data.by_source.map((s, i) => (
                                                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #3a3a3a', fontSize: '12px' }}>
                                                                <span style={{ color: '#d1d5db' }}>{s.source}</span>
                                                                <span style={{ color: '#60a5fa' }}>{(s.gallons / 1000).toFixed(0)}K gal ({s.percentage}%)</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* By Use */}
                                                {message.footprint_data.by_use?.length > 0 && (
                                                    <div style={{ marginBottom: '20px' }}>
                                                        <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '4px', color: '#ffffff' }}>By Use (Meter Logs)</h4>
                                                        <div style={{ fontSize: '10px', color: '#6b7280', marginBottom: '8px' }}>Based on meter readings — partial coverage of total withdrawal</div>
                                                        {message.footprint_data.by_use.slice(0, 5).map((u, i) => (
                                                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #3a3a3a', fontSize: '12px' }}>
                                                                <span style={{ color: '#d1d5db' }}>{u.use}</span>
                                                                <span style={{ color: '#10b981' }}>{(u.gallons / 1000).toFixed(0)}K gal ({u.percentage}%)</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* Supply Chain Breakdown */}
                                                {message.footprint_data.supply_chain?.breakdown?.length > 0 && (
                                                    <div style={{ marginBottom: '20px' }}>
                                                        <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#ffffff' }}>Top Supply Chain Contributors</h4>
                                                        {message.footprint_data.supply_chain.breakdown.map((s, i) => (
                                                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #3a3a3a', fontSize: '12px' }}>
                                                                <span style={{ color: '#d1d5db' }}>{s.supplier} <span style={{ color: '#6b7280' }}>({s.category})</span></span>
                                                                <span style={{ color: '#f59e0b' }}>{(s.footprint_gallons / 1000).toFixed(0)}K gal</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}

                                                {/* Water Intensity */}
                                                {(message.footprint_data.intensity?.per_million_revenue_gal > 0 || message.footprint_data.intensity?.per_employee_gal > 0) && (
                                                    <div>
                                                        <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>Water Intensity</h4>
                                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                                                            <div style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                                <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>Per $1M Revenue</div>
                                                                <div style={{ fontSize: '14px', fontWeight: '600', color: '#ffffff' }}>
                                                                    {(message.footprint_data.intensity.per_million_revenue_gal || 0).toLocaleString()} gal
                                                                </div>
                                                            </div>
                                                            <div style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                                <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>Per Employee</div>
                                                                <div style={{ fontSize: '14px', fontWeight: '600', color: '#ffffff' }}>
                                                                    {(message.footprint_data.intensity.per_employee_gal || 0).toLocaleString()} gal
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </div>
                                )}

                                {message.engagement_plan && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>
                                            {message.engagement_plan.plan_name}
                                        </h4>

                                        {/* Summary */}
                                        <div style={{ padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #60a5fa', marginBottom: '20px' }}>
                                            <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px' }}>Engagement Strategy Overview</div>
                                            <div style={{ fontSize: '13px', color: '#ffffff' }}>
                                                Tiered approach to engage {message.engagement_plan.total_suppliers} suppliers based on water risk and spend
                                            </div>
                                        </div>

                                        {/* Engagement Tiers */}
                                        {message.engagement_plan.tiers.map((tier, idx) => (
                                            <div key={idx} style={{ marginBottom: '20px', padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                                                    <div>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: tier.tier === 1 ? '#ef4444' : tier.tier === 2 ? '#f59e0b' : '#10b981' }}>
                                                            Tier {tier.tier}: {tier.name}
                                                        </div>
                                                        <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '2px' }}>
                                                            {tier.criteria}
                                                        </div>
                                                    </div>
                                                    <div style={{
                                                        padding: '6px 12px',
                                                        borderRadius: '6px',
                                                        background: tier.tier === 1 ? '#7f1d1d' : tier.tier === 2 ? '#78350f' : '#14532d',
                                                        border: `1px solid ${tier.tier === 1 ? '#ef4444' : tier.tier === 2 ? '#f59e0b' : '#10b981'}`
                                                    }}>
                                                        <div style={{ fontSize: '11px', fontWeight: '600', color: tier.tier === 1 ? '#ef4444' : tier.tier === 2 ? '#f59e0b' : '#10b981' }}>
                                                            {tier.supplier_count} Suppliers
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Suppliers in this tier */}
                                                {tier.suppliers.length > 0 && (
                                                    <div style={{ marginBottom: '12px' }}>
                                                        <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '6px', fontWeight: '600' }}>Suppliers:</div>
                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                                            {tier.suppliers.map((supplier, sidx) => (
                                                                <div key={sidx} style={{ padding: '4px 8px', background: '#2a2a2a', borderRadius: '4px', fontSize: '10px', color: '#ffffff' }}>
                                                                    {supplier.name}
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}

                                                {/* Actions */}
                                                <div style={{ marginBottom: '12px' }}>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '6px', fontWeight: '600' }}>Actions:</div>
                                                    <div style={{ display: 'grid', gap: '6px' }}>
                                                        {tier.actions.map((action, aidx) => (
                                                            <div key={aidx} style={{ padding: '8px', background: '#2a2a2a', borderRadius: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                                <div style={{ fontSize: '10px', color: '#ffffff', flex: 1 }}>
                                                                    {action.action}
                                                                </div>
                                                                <div style={{ fontSize: '9px', color: '#9ca3af', marginLeft: '8px', whiteSpace: 'nowrap' }}>
                                                                    {action.timeline} | {action.owner}
                                                                </div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>

                                                {/* Goals */}
                                                <div style={{ padding: '8px', background: '#2a2a2a', borderRadius: '4px' }}>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px', fontWeight: '600' }}>Goals:</div>
                                                    <div style={{ fontSize: '10px', color: '#ffffff' }}>
                                                        {Object.entries(tier.goals).map(([key, value], gidx) => (
                                                            <div key={gidx}>• {key.replace(/_/g, ' ')}: {value}</div>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}

                                        {/* Timeline */}
                                        <div style={{ marginBottom: '20px' }}>
                                            <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>
                                                2026 Implementation Timeline
                                            </h4>
                                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px' }}>
                                                {Object.entries(message.engagement_plan.timeline).map(([quarter, activities], idx) => (
                                                    <div key={idx} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ fontSize: '11px', fontWeight: '600', color: '#60a5fa', marginBottom: '6px' }}>
                                                            {quarter.replace('_', ' ').toUpperCase()}
                                                        </div>
                                                        <div style={{ fontSize: '10px', color: '#ffffff' }}>
                                                            {activities.map((activity, aidx) => (
                                                                <div key={aidx} style={{ marginBottom: '2px' }}>• {activity}</div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* KPIs */}
                                        <div style={{ marginBottom: '20px' }}>
                                            <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>
                                                Key Performance Indicators
                                            </h4>
                                            <div style={{ display: 'grid', gap: '8px' }}>
                                                {message.engagement_plan.kpis.map((kpi, idx) => (
                                                    <div key={idx} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                        <div style={{ fontSize: '11px', color: '#ffffff' }}>{kpi.metric}</div>
                                                        <div style={{ fontSize: '11px', fontWeight: '600', color: '#10b981' }}>Target: {kpi.target}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Resources */}
                                        <div>
                                            <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>
                                                Required Resources
                                            </h4>
                                            <div style={{ display: 'grid', gap: '8px' }}>
                                                {message.engagement_plan.resources.map((resource, idx) => (
                                                    <div key={idx} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                                            <div style={{ fontSize: '11px', fontWeight: '600', color: '#60a5fa' }}>{resource.resource}</div>
                                                            <div style={{ fontSize: '11px', fontWeight: '600', color: '#f59e0b' }}>{resource.cost}</div>
                                                        </div>
                                                        <div style={{ fontSize: '10px', color: '#9ca3af' }}>{resource.description}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {message.dashboard_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        {/* Summary Cards */}
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                                            <div style={{ padding: '16px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>Total Water Usage</div>
                                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#60a5fa' }}>
                                                    {(message.dashboard_data.total_usage / 1000000).toFixed(2)}M
                                                </div>
                                                <div style={{ fontSize: '10px', color: '#9ca3af' }}>gallons/month</div>
                                            </div>
                                            <div style={{ padding: '16px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>Total Cost</div>
                                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#10b981' }}>
                                                    ${(message.dashboard_data.total_cost / 1000).toFixed(1)}K
                                                </div>
                                                <div style={{ fontSize: '10px', color: '#9ca3af' }}>per month</div>
                                            </div>
                                            <div style={{ padding: '16px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>Facilities</div>
                                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#f59e0b' }}>
                                                    {message.dashboard_data.facilities.total}
                                                </div>
                                                <div style={{ fontSize: '10px', color: '#9ca3af' }}>locations tracked</div>
                                            </div>
                                            <div style={{ padding: '16px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>Compliance Rate</div>
                                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#10b981' }}>
                                                    {message.dashboard_data.compliance.rate}%
                                                </div>
                                                <div style={{ fontSize: '10px', color: '#9ca3af' }}>{message.dashboard_data.compliance.passed_tests}/{message.dashboard_data.compliance.total_tests} tests</div>
                                            </div>
                                        </div>

                                        {/* Consumption by Facility */}
                                        <div style={{ marginBottom: '20px' }}>
                                            <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                Water Consumption by Facility
                                            </h4>
                                            {message.dashboard_data.facilities.list.map((facility, idx) => {
                                                const percentage = (facility.usage / message.dashboard_data.total_usage * 100).toFixed(1);
                                                return (
                                                    <div key={idx} style={{ marginBottom: '12px' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '12px' }}>
                                                            <span style={{ color: '#ffffff' }}>{facility.name}</span>
                                                            <span style={{ color: '#9ca3af' }}>{facility.usage.toLocaleString()} gal ({percentage}%)</span>
                                                        </div>
                                                        <div style={{ width: '100%', height: '8px', background: '#3a3a3a', borderRadius: '4px', overflow: 'hidden' }}>
                                                            <div style={{ width: `${percentage}%`, height: '100%', background: idx === 2 ? '#ef4444' : idx === 1 ? '#f59e0b' : '#10b981', transition: 'width 0.3s' }}></div>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>

                                        {/* Key Insights */}
                                        <div style={{ marginBottom: '20px' }}>
                                            <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                Key Insights
                                            </h4>
                                            {message.dashboard_data.insights.map((insight, idx) => (
                                                <div key={idx} style={{
                                                    padding: '12px',
                                                    background: '#1a1a1a',
                                                    borderRadius: '6px',
                                                    border: `1px solid ${insight.type === 'warning' ? '#f59e0b' : insight.type === 'success' ? '#10b981' : '#3a3a3a'}`,
                                                    marginBottom: '8px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '8px'
                                                }}>
                                                    <span style={{ fontSize: '16px' }}>
                                                        {insight.type === 'warning' ? '⚠️' : insight.type === 'success' ? '✅' : 'ℹ️'}
                                                    </span>
                                                    <span style={{ fontSize: '12px', color: '#ffffff' }}>{insight.message}</span>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Recommendations */}
                                        <div>
                                            <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                Recommendations
                                                <span style={{ fontSize: '10px', padding: '2px 8px', background: '#0d9488', color: '#fff', borderRadius: '10px', fontWeight: '500' }}>📊 From Your Data</span>
                                            </h4>
                                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px' }}>
                                                {message.dashboard_data.recommendations.map((rec, idx) => (
                                                    <div key={idx} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa', marginBottom: '4px' }}>
                                                            {rec.title}
                                                        </div>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>
                                                            Impact: <span style={{ color: rec.impact === 'High' ? '#ef4444' : '#f59e0b' }}>{rec.impact}</span>
                                                        </div>
                                                        <div style={{ fontSize: '11px', color: '#10b981' }}>
                                                            Potential Savings: {rec.savings}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* Compliance & Permits */}
                                {message.compliance_data && message.compliance_data.has_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>📋 Compliance & Permits</h4>

                                        {/* Summary Cards */}
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px', marginBottom: '20px' }}>
                                            {[
                                                { label: 'Permits', value: message.compliance_data.total_permits, color: '#60a5fa' },
                                                { label: 'Parameters Tested', value: message.compliance_data.total_parameters_tested, color: '#9ca3af' },
                                                { label: 'Passed', value: message.compliance_data.passed_parameters, color: '#10b981' },
                                                { label: 'Violations', value: message.compliance_data.violation_count, color: message.compliance_data.violation_count > 0 ? '#ef4444' : '#10b981' },
                                            ].map((s, i) => (
                                                <div key={i} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a', textAlign: 'center' }}>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>{s.label}</div>
                                                    <div style={{ fontSize: '22px', fontWeight: '700', color: s.color }}>{s.value}</div>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Status Banner */}
                                        <div style={{
                                            padding: '10px 14px', borderRadius: '6px', marginBottom: '20px',
                                            background: message.compliance_data.status === 'Compliant' ? '#064e3b' : '#7f1d1d',
                                            border: `1px solid ${message.compliance_data.status === 'Compliant' ? '#10b981' : '#ef4444'}`,
                                            display: 'flex', alignItems: 'center', gap: '8px'
                                        }}>
                                            <span style={{ fontSize: '16px' }}>{message.compliance_data.status === 'Compliant' ? '✅' : '🚨'}</span>
                                            <span style={{ fontSize: '13px', fontWeight: '600', color: message.compliance_data.status === 'Compliant' ? '#10b981' : '#ef4444' }}>
                                                {message.compliance_data.status} — {message.compliance_data.overall_compliance_rate}% compliance rate
                                            </span>
                                        </div>

                                        {/* Expiring Permits */}
                                        {message.compliance_data.expiring_soon?.length > 0 && (
                                            <div style={{ marginBottom: '20px' }}>
                                                <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#f59e0b' }}>⚠️ Expiring Soon</h4>
                                                {message.compliance_data.expiring_soon.map((p, i) => (
                                                    <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #f59e0b', marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                        <div>
                                                            <div style={{ fontSize: '12px', fontWeight: '600', color: '#ffffff' }}>{p.permit_id}</div>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af' }}>{p.permit_type}</div>
                                                        </div>
                                                        <div style={{ textAlign: 'right' }}>
                                                            <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: '600' }}>{p.days_until_expiry} days left</div>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af' }}>Expires {p.expiration_date}</div>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}

                                        {/* Violations */}
                                        {message.compliance_data.violations?.length > 0 && (
                                            <div style={{ marginBottom: '20px' }}>
                                                <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ef4444' }}>🚨 Violations</h4>
                                                {message.compliance_data.violations.map((v, i) => (
                                                    <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #ef4444', marginBottom: '8px' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                                            <span style={{ fontSize: '12px', fontWeight: '600', color: '#ef4444' }}>{v.parameter}</span>
                                                            <span style={{ fontSize: '11px', color: '#9ca3af' }}>{v.permit_id}</span>
                                                        </div>
                                                        <div style={{ fontSize: '11px', color: '#ffffff' }}>
                                                            Measured: <span style={{ color: '#ef4444', fontWeight: '600' }}>{v.sample_value}</span>
                                                            {' '} / Limit: <span style={{ color: '#9ca3af' }}>{v.limit_value}</span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}

                                        {/* Permit Details */}
                                        <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '10px', color: '#ffffff' }}>Permit Details</h4>
                                        {message.compliance_data.permits?.map((permit, i) => (
                                            <div key={i} style={{ marginBottom: '12px', padding: '12px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                                    <div>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa' }}>{permit.permit_id}</div>
                                                        <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '2px' }}>
                                                            {permit.permit_type} · {permit.issuing_authority} · Outfall: {permit.outfall_id}
                                                        </div>
                                                    </div>
                                                    <div style={{ textAlign: 'right' }}>
                                                        <div style={{ fontSize: '11px', fontWeight: '600', color: permit.compliance_rate === 100 ? '#10b981' : '#ef4444' }}>
                                                            {permit.compliance_rate}% compliant
                                                        </div>
                                                        <div style={{ fontSize: '10px', color: '#9ca3af' }}>Expires {permit.expiration_date}</div>
                                                    </div>
                                                </div>
                                                <div style={{ display: 'flex', gap: '12px', fontSize: '11px' }}>
                                                    <span style={{ color: '#9ca3af' }}>Lab: <span style={{ color: '#d1d5db' }}>{permit.lab_name}</span></span>
                                                    <span style={{ color: '#9ca3af' }}>{permit.passed_parameters}/{permit.total_parameters} params passed</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {/* DMR Report */}
                                {message.dmr_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px', color: '#ffffff' }}>📋 Discharge Monitoring Report</h4>
                                        <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '16px' }}>
                                            {message.dmr_data.reporting_period} · Generated {message.dmr_data.generated_date}
                                            <span style={{ marginLeft: '8px', padding: '2px 8px', background: '#065f46', color: '#6ee7b7', borderRadius: '8px', fontSize: '10px' }}>📊 Real Data</span>
                                        </div>

                                        {(message.dmr_data.permits || []).map((permit, i) => (
                                            <div key={i} style={{ marginBottom: '16px', padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                {/* Permit header */}
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                                                    <div>
                                                        <div style={{ fontSize: '13px', fontWeight: '700', color: '#60a5fa' }}>{permit.permit_id}</div>
                                                        <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '2px' }}>
                                                            {permit.permit_type} · {permit.issuing_authority} · Outfall: {permit.outfall_id} · Lab: {permit.lab_name}
                                                        </div>
                                                    </div>
                                                    <div style={{
                                                        padding: '4px 10px', borderRadius: '6px', fontSize: '11px', fontWeight: '700',
                                                        background: permit.overall_status === 'Compliant' ? '#064e3b' : '#7f1d1d',
                                                        color: permit.overall_status === 'Compliant' ? '#10b981' : '#ef4444',
                                                        border: `1px solid ${permit.overall_status === 'Compliant' ? '#10b981' : '#ef4444'}`
                                                    }}>{permit.overall_status}</div>
                                                </div>

                                                {/* Stats row */}
                                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '12px' }}>
                                                    {[
                                                        { label: 'Discharge Volume', value: `${(permit.discharge_volume_gallons || 0).toLocaleString()} gal` },
                                                        { label: 'Avg Daily Flow', value: `${(permit.avg_daily_flow_gallons || 0).toLocaleString()} gal/day` },
                                                        { label: 'Compliance Rate', value: `${permit.compliance_rate}%` },
                                                    ].map((s, j) => (
                                                        <div key={j} style={{ padding: '8px', background: '#2a2a2a', borderRadius: '6px', textAlign: 'center' }}>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '2px' }}>{s.label}</div>
                                                            <div style={{ fontSize: '13px', fontWeight: '600', color: '#ffffff' }}>{s.value}</div>
                                                        </div>
                                                    ))}
                                                </div>

                                                {/* Parameters table */}
                                                <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
                                                    <thead>
                                                        <tr style={{ borderBottom: '1px solid #4a4a4a' }}>
                                                            {['Parameter', 'Average', 'Maximum', 'Limit', 'Unit', 'Status'].map(h => (
                                                                <th key={h} style={{ padding: '6px 8px', color: '#9ca3af', textAlign: 'left', fontWeight: '500' }}>{h}</th>
                                                            ))}
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {(permit.parameters || []).map((param, j) => (
                                                            <tr key={j} style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                                <td style={{ padding: '6px 8px', color: '#d1d5db' }}>{param.name}</td>
                                                                <td style={{ padding: '6px 8px', color: '#ffffff' }}>{param.average_value}</td>
                                                                <td style={{ padding: '6px 8px', color: '#ffffff' }}>{param.max_value}</td>
                                                                <td style={{ padding: '6px 8px', color: '#9ca3af' }}>{param.limit}</td>
                                                                <td style={{ padding: '6px 8px', color: '#9ca3af' }}>{param.unit}</td>
                                                                <td style={{ padding: '6px 8px' }}>
                                                                    <span style={{
                                                                        padding: '2px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: '600',
                                                                        background: param.status === 'pass' ? '#064e3b' : '#7f1d1d',
                                                                        color: param.status === 'pass' ? '#10b981' : '#ef4444'
                                                                    }}>{param.status === 'pass' ? '✅ Pass' : '❌ Fail'}</span>
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        ))}

                                        {/* Recommendations */}
                                        {message.dmr_data.recommendations?.length > 0 && (
                                            <div style={{ marginBottom: '12px' }}>
                                                <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '6px', fontWeight: '600' }}>Recommendations</div>
                                                {message.dmr_data.recommendations.map((r, i) => (
                                                    <div key={i} style={{ fontSize: '11px', color: '#d1d5db', padding: '4px 0', borderBottom: '1px solid #3a3a3a' }}>• {r}</div>
                                                ))}
                                            </div>
                                        )}

                                        {/* Certification */}
                                        <div style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #1d4ed8', fontSize: '10px', color: '#9ca3af', fontStyle: 'italic' }}>
                                            {message.dmr_data.certification}
                                        </div>
                                    </div>
                                )}

                                {/* Stewardship Strategy */}
                                {message.strategy_data && (
                                    <div style={{ marginTop: '12px', padding: '20px', background: '#2a2a2a', border: '1px solid #2563eb', borderRadius: '10px' }}>
                                        {/* Header */}
                                        <div style={{ borderBottom: '2px solid #2563eb', paddingBottom: '12px', marginBottom: '16px' }}>
                                            <div style={{ fontSize: '16px', fontWeight: '700', color: '#60a5fa' }}>💧 Water Stewardship Strategy</div>
                                            <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>Generated {message.strategy_data.generated_date} · ✨ AI Generated</div>
                                        </div>

                                        {/* Target banner */}
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '10px', marginBottom: '20px' }}>
                                            {[
                                                { label: 'Reduction Target', value: `${message.strategy_data.target_reduction_pct || 30}%`, color: '#60a5fa' },
                                                { label: 'Target Year', value: message.strategy_data.target_year || 2027, color: '#10b981' },
                                                { label: 'Current Usage', value: `${((message.strategy_data.total_gal || 0) / 1000000).toFixed(2)}M gal`, color: '#f59e0b' },
                                                { label: 'Annual Cost', value: `$${((message.strategy_data.total_cost || 0) / 1000).toFixed(0)}K`, color: '#9ca3af' },
                                            ].map((item, i) => (
                                                <div key={i} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a', textAlign: 'center' }}>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>{item.label}</div>
                                                    <div style={{ fontSize: '18px', fontWeight: '700', color: item.color }}>{item.value}</div>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Executive summary */}
                                        <div style={{ padding: '14px 16px', background: '#1a1a1a', borderLeft: '4px solid #2563eb', borderRadius: '0 8px 8px 0', marginBottom: '20px', fontSize: '13px', lineHeight: '1.7', color: '#d1d5db' }}>
                                            {message.strategy_data.executive_summary}
                                        </div>

                                        {/* Priorities */}
                                        <div style={{ fontSize: '13px', fontWeight: '700', color: '#ffffff', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            <div style={{ width: '4px', height: '16px', background: '#2563eb', borderRadius: '2px' }}></div>
                                            Strategic Priorities
                                        </div>
                                        <div style={{ display: 'grid', gap: '10px', marginBottom: '20px' }}>
                                            {(message.strategy_data.priorities || []).map((p, i) => (
                                                <div key={i} style={{ display: 'flex', gap: '12px', padding: '12px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                    <div style={{ width: '28px', height: '28px', background: '#2563eb', color: 'white', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: '700', flexShrink: 0 }}>
                                                        {p.rank}
                                                    </div>
                                                    <div style={{ flex: 1 }}>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#ffffff', marginBottom: '3px' }}>{p.title}</div>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px' }}>{p.description}</div>
                                                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                                            <span style={{ padding: '2px 10px', background: '#064e3b', color: '#6ee7b7', borderRadius: '10px', fontSize: '10px', fontWeight: '600' }}>{p.impact}</span>
                                                            <span style={{ padding: '2px 10px', background: '#1e3a5f', color: '#93c5fd', borderRadius: '10px', fontSize: '10px', fontWeight: '600' }}>{p.timeline}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>

                                        {/* KPIs */}
                                        <div style={{ fontSize: '13px', fontWeight: '700', color: '#ffffff', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            <div style={{ width: '4px', height: '16px', background: '#2563eb', borderRadius: '2px' }}></div>
                                            Key Performance Indicators
                                        </div>
                                        <div style={{ overflowX: 'auto', marginBottom: '20px' }}>
                                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                                                <thead>
                                                    <tr style={{ borderBottom: '2px solid #3a3a3a' }}>
                                                        {['Metric', 'Baseline', 'Target', 'Frequency'].map(h => (
                                                            <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: '#9ca3af', fontWeight: '600' }}>{h}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {(message.strategy_data.kpis || []).map((k, i) => (
                                                        <tr key={i} style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 10px', color: '#ffffff' }}>{k.metric}</td>
                                                            <td style={{ padding: '8px 10px', color: '#9ca3af' }}>{k.baseline}</td>
                                                            <td style={{ padding: '8px 10px', color: '#10b981', fontWeight: '600' }}>{k.target}</td>
                                                            <td style={{ padding: '8px 10px', color: '#9ca3af' }}>{k.frequency}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>

                                        {/* Timeline */}
                                        <div style={{ fontSize: '13px', fontWeight: '700', color: '#ffffff', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            <div style={{ width: '4px', height: '16px', background: '#2563eb', borderRadius: '2px' }}></div>
                                            Implementation Timeline
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
                                            {(message.strategy_data.timeline || []).map((t, i) => (
                                                <div key={i} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a' }}>
                                                    <div style={{ fontSize: '12px', fontWeight: '700', color: '#60a5fa', marginBottom: '2px' }}>{t.phase}</div>
                                                    <div style={{ fontSize: '10px', color: '#6b7280', marginBottom: '8px' }}>{t.period}</div>
                                                    {(t.actions || []).map((a, j) => (
                                                        <div key={j} style={{ fontSize: '11px', color: '#d1d5db', padding: '2px 0' }}>• {a}</div>
                                                    ))}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Efficiency Opportunities */}
                                {message.efficiency_data && message.efficiency_data.has_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>📈 Efficiency Opportunities</h4>

                                        {/* Summary row */}
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px', marginBottom: '20px' }}>
                                            {[
                                                { label: 'Opportunities', value: message.efficiency_data.opportunity_count, color: '#60a5fa' },
                                                { label: 'Potential Savings', value: `$${(message.efficiency_data.total_potential_savings_usd / 1000).toFixed(1)}K/yr`, color: '#10b981' },
                                                { label: 'Water Saved', value: `${(message.efficiency_data.total_potential_savings_gallons / 1000).toFixed(0)}K gal`, color: '#60a5fa' },
                                                { label: 'Total Investment', value: `$${(message.efficiency_data.total_investment_required / 1000).toFixed(0)}K`, color: '#f59e0b' },
                                            ].map((s, i) => (
                                                <div key={i} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a', textAlign: 'center' }}>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>{s.label}</div>
                                                    <div style={{ fontSize: '16px', fontWeight: '700', color: s.color }}>{s.value}</div>
                                                </div>
                                            ))}
                                        </div>

                                        {/* Opportunity cards */}
                                        <div style={{ display: 'grid', gap: '12px' }}>
                                            {message.efficiency_data.opportunities.map((opp, i) => (
                                                <div key={i} style={{ padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: `1px solid ${opp.priority === 'Immediate' ? '#ef4444' : opp.priority === 'High' ? '#f59e0b' : '#3a3a3a'}` }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                                        <div>
                                                            <div style={{ fontSize: '13px', fontWeight: '600', color: '#ffffff' }}>{opp.name}</div>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '2px' }}>{opp.detail}</div>
                                                        </div>
                                                        <div style={{ display: 'flex', gap: '6px', flexShrink: 0, marginLeft: '8px' }}>
                                                            <span style={{
                                                                padding: '3px 8px', borderRadius: '10px', fontSize: '10px', fontWeight: '600',
                                                                background: opp.priority === 'Immediate' ? '#7f1d1d' : opp.priority === 'High' ? '#78350f' : '#1e3a5f',
                                                                color: opp.priority === 'Immediate' ? '#ef4444' : opp.priority === 'High' ? '#f59e0b' : '#60a5fa'
                                                            }}>{opp.priority}</span>
                                                            <span style={{ padding: '3px 8px', borderRadius: '10px', fontSize: '10px', background: '#1a2a1a', color: '#10b981' }}>{opp.category}</span>
                                                        </div>
                                                    </div>
                                                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', fontSize: '11px' }}>
                                                        <div style={{ padding: '8px', background: '#2a2a2a', borderRadius: '6px' }}>
                                                            <div style={{ color: '#9ca3af', marginBottom: '2px' }}>Annual Savings</div>
                                                            <div style={{ color: '#10b981', fontWeight: '600' }}>${opp.savings_cost_year.toLocaleString()}</div>
                                                        </div>
                                                        <div style={{ padding: '8px', background: '#2a2a2a', borderRadius: '6px' }}>
                                                            <div style={{ color: '#9ca3af', marginBottom: '2px' }}>Water Saved</div>
                                                            <div style={{ color: '#60a5fa', fontWeight: '600' }}>{(opp.savings_gallons_year / 1000).toFixed(0)}K gal</div>
                                                        </div>
                                                        <div style={{ padding: '8px', background: '#2a2a2a', borderRadius: '6px' }}>
                                                            <div style={{ color: '#9ca3af', marginBottom: '2px' }}>Payback</div>
                                                            <div style={{ color: '#f59e0b', fontWeight: '600' }}>{opp.payback_months} mo</div>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Industry Comparison */}
                                {message.industry_comparison_data && message.industry_comparison_data.has_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>📊 Industry Benchmark Comparison</h4>
                                        {/* Score cards */}
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px', marginBottom: '20px' }}>
                                            {[
                                                { label: 'Your Intensity', value: `${(message.industry_comparison_data.your_intensity || 0).toLocaleString()}`, sub: 'gal/$1M revenue', color: '#60a5fa' },
                                                { label: 'Industry Average', value: `${(message.industry_comparison_data.industry_average || 0).toLocaleString()}`, sub: 'gal/$1M revenue', color: '#9ca3af' },
                                                { label: 'Best-in-Class', value: `${(message.industry_comparison_data.best_in_class || 0).toLocaleString()}`, sub: 'gal/$1M revenue', color: '#10b981' },
                                            ].map((s, i) => (
                                                <div key={i} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '8px', border: '1px solid #3a3a3a', textAlign: 'center' }}>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>{s.label}</div>
                                                    <div style={{ fontSize: '18px', fontWeight: '700', color: s.color }}>{s.value}</div>
                                                    <div style={{ fontSize: '10px', color: '#6b7280' }}>{s.sub}</div>
                                                </div>
                                            ))}
                                        </div>
                                        {/* vs average banner */}
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '20px' }}>
                                            {[
                                                { label: 'vs Industry Average', val: message.industry_comparison_data.vs_average_pct },
                                                { label: 'vs Best-in-Class', val: message.industry_comparison_data.vs_best_pct },
                                            ].map((item, i) => (
                                                <div key={i} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '8px', border: `1px solid ${item.val > 0 ? '#f59e0b' : '#10b981'}`, textAlign: 'center' }}>
                                                    <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '4px' }}>{item.label}</div>
                                                    <div style={{ fontSize: '20px', fontWeight: '700', color: item.val > 0 ? '#f59e0b' : '#10b981' }}>
                                                        {item.val > 0 ? '+' : ''}{item.val}%
                                                    </div>
                                                    <div style={{ fontSize: '10px', color: item.val > 0 ? '#f59e0b' : '#10b981' }}>
                                                        {item.val > 0 ? '↑ Above — room to improve' : '↓ Below — great performance'}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        {/* Per-facility */}
                                        {message.industry_comparison_data.facility_comparisons?.length > 0 && (
                                            <div>
                                                <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '8px', fontWeight: '600' }}>By Facility</div>
                                                {message.industry_comparison_data.facility_comparisons.map((f, i) => (
                                                    <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a', marginBottom: '8px' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                                            <span style={{ fontSize: '12px', color: '#ffffff', fontWeight: '600' }}>{f.facility}</span>
                                                            <span style={{ fontSize: '11px', color: '#9ca3af' }}>{f.type}</span>
                                                        </div>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                                                            <span style={{ color: '#9ca3af' }}>Intensity: <span style={{ color: '#60a5fa', fontWeight: '600' }}>{(f.intensity_gal_per_m_revenue || 0).toLocaleString()} gal/$1M</span></span>
                                                            <span style={{ color: f.vs_average_pct > 0 ? '#f59e0b' : '#10b981', fontWeight: '600' }}>
                                                                {f.vs_average_pct > 0 ? '+' : ''}{f.vs_average_pct}% vs avg
                                                            </span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Reduction Targets */}
                                {message.reduction_targets_data && message.reduction_targets_data.has_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '8px', color: '#ffffff' }}>🎯 Water Reduction Targets</h4>
                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '16px' }}>
                                            Baseline: {(message.reduction_targets_data.baseline_gallons / 1000).toFixed(0)}K gal · Cost: ${(message.reduction_targets_data.baseline_cost_usd / 1000).toFixed(1)}K
                                        </div>
                                        <div style={{ display: 'grid', gap: '12px' }}>
                                            {message.reduction_targets_data.scenarios.map((s, i) => (
                                                <div key={i} style={{ padding: '14px', background: '#1a1a1a', borderRadius: '8px', border: `1px solid ${i === 0 ? '#10b981' : i === 1 ? '#60a5fa' : '#f59e0b'}` }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                                                        <div>
                                                            <span style={{ fontSize: '13px', fontWeight: '700', color: i === 0 ? '#10b981' : i === 1 ? '#60a5fa' : '#f59e0b' }}>
                                                                {s.label} — {s.reduction_pct}% by {s.target_year}
                                                            </span>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '2px' }}>
                                                                {(s.baseline_gallons / 1000).toFixed(0)}K → {(s.target_gallons / 1000).toFixed(0)}K gal
                                                            </div>
                                                        </div>
                                                        <div style={{ textAlign: 'right' }}>
                                                            <div style={{ fontSize: '14px', fontWeight: '700', color: '#10b981' }}>${(s.annual_cost_savings_usd / 1000).toFixed(1)}K/yr</div>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af' }}>saved</div>
                                                        </div>
                                                    </div>
                                                    {s.initiatives.length > 0 && (
                                                        <div style={{ borderTop: '1px solid #3a3a3a', paddingTop: '8px' }}>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '6px' }}>Key initiatives:</div>
                                                            {s.initiatives.map((init, j) => (
                                                                <div key={j} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', padding: '3px 0' }}>
                                                                    <span style={{ color: '#d1d5db' }}>• {init.name}</span>
                                                                    <span style={{ color: '#10b981' }}>{(init.savings_gal / 1000).toFixed(0)}K gal saved</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Footprint Hotspots */}
                                {message.footprint_hotspots_data && message.footprint_hotspots_data.has_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>📈 Water Usage Hotspots</h4>
                                        {/* Insights */}
                                        {message.footprint_hotspots_data.insights?.length > 0 && (
                                            <div style={{ marginBottom: '16px' }}>
                                                {message.footprint_hotspots_data.insights.map((ins, i) => (
                                                    <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: `1px solid ${ins.type === 'critical' ? '#ef4444' : ins.type === 'warning' ? '#f59e0b' : '#3a3a3a'}`, marginBottom: '8px', display: 'flex', gap: '8px', alignItems: 'center' }}>
                                                        <span>{ins.type === 'critical' ? '🚨' : ins.type === 'warning' ? '⚠️' : 'ℹ️'}</span>
                                                        <span style={{ fontSize: '12px', color: '#ffffff' }}>{ins.message}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {/* By facility bars */}
                                        <div style={{ marginBottom: '16px' }}>
                                            <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '8px', fontWeight: '600' }}>By Facility</div>
                                            {message.footprint_hotspots_data.by_facility.map((f, i) => (
                                                <div key={i} style={{ marginBottom: '10px' }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '12px' }}>
                                                        <span style={{ color: '#ffffff' }}>
                                                            {f.facility}
                                                            {f.is_hotspot && <span style={{ marginLeft: '6px', fontSize: '10px', padding: '1px 6px', background: '#7f1d1d', color: '#ef4444', borderRadius: '8px' }}>HOTSPOT</span>}
                                                        </span>
                                                        <span style={{ color: '#9ca3af' }}>{(f.gallons / 1000).toFixed(0)}K gal ({f.percentage}%)</span>
                                                    </div>
                                                    <div style={{ background: '#3a3a3a', borderRadius: '3px', height: '8px' }}>
                                                        <div style={{ width: `${f.percentage}%`, height: '100%', background: f.is_hotspot ? '#ef4444' : i === 1 ? '#f59e0b' : '#10b981', borderRadius: '3px' }} />
                                                    </div>
                                                    {f.intensity_gal_per_employee > 0 && (
                                                        <div style={{ fontSize: '10px', color: '#6b7280', marginTop: '2px' }}>{f.intensity_gal_per_employee.toLocaleString()} gal/employee</div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                        {/* Supply chain hotspots */}
                                        {message.footprint_hotspots_data.supply_chain_hotspots?.length > 0 && (
                                            <div>
                                                <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '8px', fontWeight: '600' }}>Top Supply Chain Hotspots</div>
                                                {message.footprint_hotspots_data.supply_chain_hotspots.map((s, i) => (
                                                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #3a3a3a', fontSize: '12px' }}>
                                                        <span style={{ color: '#d1d5db' }}>{s.supplier} <span style={{ color: '#6b7280' }}>({s.category})</span></span>
                                                        <span style={{ color: '#f59e0b', fontWeight: '600' }}>{(s.footprint_gallons / 1000).toFixed(0)}K gal</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Footprint Report (combined view) */}
                                {message.footprint_report_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px', color: '#ffffff' }}>📋 Water Footprint Report</h4>
                                        {/* Footprint summary */}
                                        {message.footprint_report_data.footprint?.has_data && (
                                            <div style={{ marginBottom: '16px' }}>
                                                <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '8px', fontWeight: '600' }}>Direct Footprint</div>
                                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                                                    {[
                                                        { label: 'Withdrawal', val: message.footprint_report_data.footprint.direct?.total_withdrawal_gallons, color: '#60a5fa' },
                                                        { label: 'Consumed', val: message.footprint_report_data.footprint.direct?.consumption_gallons, color: '#f59e0b' },
                                                        { label: 'Discharged', val: message.footprint_report_data.footprint.direct?.discharge_gallons, color: '#10b981' },
                                                        { label: 'Supply Chain', val: message.footprint_report_data.footprint.supply_chain?.total_gallons, color: '#9ca3af' },
                                                    ].map((item, i) => (
                                                        <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                            <div style={{ fontSize: '10px', color: '#9ca3af', marginBottom: '2px' }}>{item.label}</div>
                                                            <div style={{ fontSize: '14px', fontWeight: '600', color: item.color }}>
                                                                {((item.val || 0) / 1000).toFixed(0)}K gal
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                        {/* Industry comparison summary */}
                                        {message.footprint_report_data.industry?.has_data && (
                                            <div style={{ marginBottom: '16px', padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '6px', fontWeight: '600' }}>Industry Comparison</div>
                                                <div style={{ fontSize: '12px', color: '#ffffff' }}>
                                                    Your intensity: <span style={{ color: '#60a5fa', fontWeight: '600' }}>{(message.footprint_report_data.industry.your_intensity || 0).toLocaleString()} gal/$1M</span>
                                                    {' '}vs avg <span style={{ color: '#9ca3af' }}>{(message.footprint_report_data.industry.industry_average || 0).toLocaleString()}</span>
                                                    {' '}— <span style={{ color: message.footprint_report_data.industry.vs_average_pct > 0 ? '#f59e0b' : '#10b981', fontWeight: '600' }}>
                                                        {message.footprint_report_data.industry.vs_average_pct > 0 ? '+' : ''}{message.footprint_report_data.industry.vs_average_pct}% vs average
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                        <div style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #10b981', fontSize: '12px', color: '#10b981', textAlign: 'center' }}>
                                            Click "💾 Download Report" to get the full HTML report
                                        </div>
                                    </div>
                                )}

                                {/* Trends (12 months) */}
                                {message.trends_data && message.trends_data.has_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>📈 Water Usage Trends</h4>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
                                            {[
                                                { label: 'Avg Monthly', value: `${(message.trends_data.stats.average_monthly_gallons / 1000).toFixed(0)}K gal` },
                                                { label: 'Peak Month', value: message.trends_data.stats.peak_month },
                                                { label: 'Months Tracked', value: message.trends_data.stats.months_tracked },
                                            ].map((s, i) => (
                                                <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', textAlign: 'center' }}>
                                                    <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>{s.label}</div>
                                                    <div style={{ fontSize: '16px', fontWeight: '700', color: '#60a5fa' }}>{s.value}</div>
                                                </div>
                                            ))}
                                        </div>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                            {message.trends_data.monthly_trends.map((m, i) => {
                                                const max = Math.max(...message.trends_data.monthly_trends.map(x => x.volume_gallons));
                                                const pct = max > 0 ? (m.volume_gallons / max * 100).toFixed(0) : 0;
                                                return (
                                                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                        <div style={{ width: '60px', fontSize: '11px', color: '#9ca3af', flexShrink: 0 }}>{m.month}</div>
                                                        <div style={{ flex: 1, background: '#3a3a3a', borderRadius: '3px', height: '16px', overflow: 'hidden' }}>
                                                            <div style={{ width: `${pct}%`, height: '100%', background: '#3b82f6', borderRadius: '3px' }} />
                                                        </div>
                                                        <div style={{ width: '80px', fontSize: '11px', color: '#ffffff', textAlign: 'right', flexShrink: 0 }}>
                                                            {(m.volume_gallons / 1000).toFixed(0)}K gal
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}

                                {/* Water Balance */}
                                {message.water_balance_data && message.water_balance_data.has_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>💧 Water Balance</h4>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
                                            {[
                                                { label: 'Withdrawal', value: `${(message.water_balance_data.total_withdrawal_gallons / 1000).toFixed(0)}K gal`, color: '#60a5fa' },
                                                { label: 'Consumption', value: `${(message.water_balance_data.total_consumption_gallons / 1000).toFixed(0)}K gal (${message.water_balance_data.consumption_rate_pct}%)`, color: '#f59e0b' },
                                                { label: 'Discharge', value: `${(message.water_balance_data.total_discharge_gallons / 1000).toFixed(0)}K gal`, color: '#10b981' },
                                            ].map((s, i) => (
                                                <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', textAlign: 'center' }}>
                                                    <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>{s.label}</div>
                                                    <div style={{ fontSize: '13px', fontWeight: '700', color: s.color }}>{s.value}</div>
                                                </div>
                                            ))}
                                        </div>
                                        {message.water_balance_data.sources.length > 0 && (
                                            <div style={{ marginBottom: '12px' }}>
                                                <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '6px' }}>Sources</div>
                                                {message.water_balance_data.sources.map((s, i) => (
                                                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #3a3a3a', fontSize: '12px' }}>
                                                        <span style={{ color: '#d1d5db' }}>{s.source}</span>
                                                        <span style={{ color: '#60a5fa' }}>{(s.volume / 1000).toFixed(0)}K gal ({s.percentage}%)</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        {message.water_balance_data.uses.length > 0 && (
                                            <div>
                                                <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '6px' }}>Uses by Location</div>
                                                {message.water_balance_data.uses.slice(0, 5).map((u, i) => (
                                                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #3a3a3a', fontSize: '12px' }}>
                                                        <span style={{ color: '#d1d5db' }}>{u.use}</span>
                                                        <span style={{ color: '#10b981' }}>{(u.volume / 1000).toFixed(0)}K gal ({u.percentage}%)</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Pollutant Levels */}
                                {message.pollutant_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>🧪 Pollutant Levels</h4>
                                        {!message.pollutant_data.has_data ? (
                                            <div style={{ color: '#9ca3af', fontSize: '13px' }}>No discharge report data available. Upload discharge reports to see pollutant levels.</div>
                                        ) : (
                                            <>
                                                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
                                                    {[
                                                        { label: 'Parameters Tested', value: message.pollutant_data.total_parameters, color: '#60a5fa' },
                                                        { label: 'Passed', value: message.pollutant_data.passed, color: '#10b981' },
                                                        { label: 'Failed', value: message.pollutant_data.failed, color: message.pollutant_data.failed > 0 ? '#ef4444' : '#10b981' },
                                                    ].map((s, i) => (
                                                        <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', textAlign: 'center' }}>
                                                            <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>{s.label}</div>
                                                            <div style={{ fontSize: '20px', fontWeight: '700', color: s.color }}>{s.value}</div>
                                                        </div>
                                                    ))}
                                                </div>
                                                <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                                                    <thead>
                                                        <tr style={{ borderBottom: '1px solid #4a4a4a' }}>
                                                            {['Parameter', 'Value', 'Limit', 'Status'].map(h => (
                                                                <th key={h} style={{ padding: '6px 8px', color: '#9ca3af', textAlign: 'left', fontWeight: '500' }}>{h}</th>
                                                            ))}
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {message.pollutant_data.results.map((r, i) => (
                                                            <tr key={i} style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                                <td style={{ padding: '6px 8px', color: '#d1d5db' }}>{r.parameter}</td>
                                                                <td style={{ padding: '6px 8px', color: '#ffffff' }}>{r.value} {r.unit}</td>
                                                                <td style={{ padding: '6px 8px', color: '#9ca3af' }}>{r.limit} {r.unit}</td>
                                                                <td style={{ padding: '6px 8px' }}>
                                                                    <span style={{
                                                                        padding: '2px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: '600',
                                                                        background: r.status === 'pass' ? '#064e3b' : '#7f1d1d',
                                                                        color: r.status === 'pass' ? '#10b981' : '#ef4444'
                                                                    }}>
                                                                        {r.status === 'pass' ? '✅ Pass' : '❌ Fail'}
                                                                    </span>
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </>
                                        )}
                                    </div>
                                )}

                                {/* Cost Analysis */}
                                {message.cost_data && message.cost_data.has_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>💰 Cost Analysis</h4>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '16px' }}>
                                            {[
                                                { label: 'Total Cost', value: `$${(message.cost_data.total_cost_usd / 1000).toFixed(1)}K`, color: '#10b981' },
                                                { label: 'Avg Rate', value: `$${message.cost_data.avg_cost_per_1000_gal}/1K gal`, color: '#f59e0b' },
                                            ].map((s, i) => (
                                                <div key={i} style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', textAlign: 'center' }}>
                                                    <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '4px' }}>{s.label}</div>
                                                    <div style={{ fontSize: '20px', fontWeight: '700', color: s.color }}>{s.value}</div>
                                                </div>
                                            ))}
                                        </div>
                                        <div style={{ marginBottom: '12px' }}>
                                            <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '8px' }}>Cost by Facility</div>
                                            {message.cost_data.by_facility.map((f, i) => (
                                                <div key={i} style={{ marginBottom: '8px' }}>
                                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '12px' }}>
                                                        <span style={{ color: '#d1d5db' }}>{f.facility}</span>
                                                        <span style={{ color: '#10b981' }}>${(f.cost_usd / 1000).toFixed(1)}K ({f.percentage}%)</span>
                                                    </div>
                                                    <div style={{ background: '#3a3a3a', borderRadius: '3px', height: '8px' }}>
                                                        <div style={{ width: `${f.percentage}%`, height: '100%', background: '#10b981', borderRadius: '3px' }} />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        {message.cost_data.monthly_cost.length > 0 && (
                                            <div>
                                                <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '6px' }}>Monthly Cost</div>
                                                {message.cost_data.monthly_cost.map((m, i) => (
                                                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #3a3a3a', fontSize: '12px' }}>
                                                        <span style={{ color: '#9ca3af' }}>{m.month}</span>
                                                        <span style={{ color: '#f59e0b' }}>${m.cost_usd.toLocaleString()}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Facility Risk Comparison */}
                                {message.facility_risk_comparison && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>📊 Facility Risk Comparison</h4>
                                        <div style={{ overflowX: 'auto' }}>
                                            <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                                                <thead>
                                                    <tr style={{ borderBottom: '1px solid #4a4a4a' }}>
                                                        <th style={{ padding: '8px', color: '#9ca3af', textAlign: 'left' }}>Risk Dimension</th>
                                                        {message.facility_risk_comparison.facilities.map((f, i) => (
                                                            <th key={i} style={{ padding: '8px', color: '#60a5fa', textAlign: 'center' }}>{f.facility_name}</th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {/* Overall row */}
                                                    <tr style={{ borderBottom: '1px solid #3a3a3a', background: '#1a1a1a' }}>
                                                        <td style={{ padding: '8px', color: '#ffffff', fontWeight: '600' }}>Overall Score</td>
                                                        {message.facility_risk_comparison.facilities.map((f, i) => {
                                                            const color = f.overall_risk_score >= 4 ? '#ef4444' : f.overall_risk_score >= 3 ? '#f59e0b' : '#10b981';
                                                            return <td key={i} style={{ padding: '8px', textAlign: 'center', color, fontWeight: '700' }}>{f.overall_risk_score}/5.0</td>;
                                                        })}
                                                    </tr>
                                                    {message.facility_risk_comparison.comparison_table.map((row, i) => (
                                                        <tr key={i} style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px', color: '#d1d5db' }}>{row.dimension}</td>
                                                            {message.facility_risk_comparison.facilities.map((f, j) => {
                                                                const cell = row[f.facility_name];
                                                                const color = !cell ? '#9ca3af' : cell.score >= 4 ? '#ef4444' : cell.score >= 3 ? '#f59e0b' : cell.score >= 2 ? '#60a5fa' : '#10b981';
                                                                return <td key={j} style={{ padding: '8px', textAlign: 'center', color, fontSize: '11px' }}>{cell ? cell.level : '—'}</td>;
                                                            })}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                )}

                                {/* Risk Map */}
                                {message.risk_map_data && message.risk_map_data.markers && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>🗺️ Water Risk Map</h4>
                                        {/* Map legend */}
                                        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '12px', fontSize: '11px' }}>
                                            {[['#10b981', 'Low'], ['#60a5fa', 'Medium'], ['#f59e0b', 'High'], ['#ef4444', 'Extremely High']].map(([c, l]) => (
                                                <span key={l} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: c, display: 'inline-block' }} />
                                                    <span style={{ color: '#9ca3af' }}>{l}</span>
                                                </span>
                                            ))}
                                        </div>
                                        {/* Facility cards as map pins */}
                                        <div style={{ display: 'grid', gap: '10px' }}>
                                            {message.risk_map_data.markers.map((m, i) => {
                                                const color = m.overall_risk_score >= 4 ? '#ef4444' : m.overall_risk_score >= 3 ? '#f59e0b' : m.overall_risk_score >= 2 ? '#60a5fa' : '#10b981';
                                                return (
                                                    <div key={i} style={{ padding: '12px', background: '#1a1a1a', borderRadius: '8px', borderLeft: `4px solid ${color}` }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                                            <div>
                                                                <div style={{ fontSize: '13px', fontWeight: '600', color: '#ffffff' }}>📍 {m.facility_name}</div>
                                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '2px' }}>{m.location}</div>
                                                                <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '2px' }}>
                                                                    {m.lat.toFixed(4)}°N, {Math.abs(m.lon).toFixed(4)}°W
                                                                </div>
                                                            </div>
                                                            <div style={{ textAlign: 'right' }}>
                                                                <div style={{ fontSize: '18px', fontWeight: '700', color }}>{m.overall_risk_score}/5.0</div>
                                                                <div style={{ fontSize: '11px', color }}>{m.overall_risk_level}</div>
                                                            </div>
                                                        </div>
                                                        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '8px' }}>
                                                            {Object.entries(m.risk_breakdown).map(([k, v]) => (
                                                                <span key={k} style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '8px', background: '#2a2a2a', color: v.score >= 4 ? '#ef4444' : v.score >= 3 ? '#f59e0b' : '#9ca3af' }}>
                                                                    {k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}: {v.level}
                                                                </span>
                                                            ))}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}

                                {/* Climate Scenarios */}
                                {message.climate_scenarios_data && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px', color: '#ffffff' }}>📈 Climate Scenarios (WRI Aqueduct)</h4>
                                        <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '12px' }}>Optimistic = RCP 2.6 · Business as Usual = RCP 4.5 · Pessimistic = RCP 8.5</div>
                                        {message.climate_scenarios_data.ai_narrative && (
                                            <div style={{ padding: '10px', background: '#1a1a1a', borderRadius: '6px', marginBottom: '12px', fontSize: '12px', color: '#d1d5db', borderLeft: '3px solid #7c3aed' }}>
                                                <span style={{ fontSize: '10px', color: '#7c3aed', fontWeight: '600' }}>✨ AI Analysis · </span>
                                                {message.climate_scenarios_data.ai_narrative}
                                            </div>
                                        )}
                                        {message.climate_scenarios_data.scenarios.map((s, i) => (
                                            <div key={i} style={{ marginBottom: '12px', padding: '12px', background: '#1a1a1a', borderRadius: '8px' }}>
                                                <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa', marginBottom: '4px' }}>{s.facility_name}</div>
                                                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px' }}>{s.location} · Current: <span style={{ color: '#f59e0b' }}>{s.current_stress}</span></div>
                                                {s.has_projection_data && s.projections ? (
                                                    <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse' }}>
                                                        <thead>
                                                            <tr>
                                                                <th style={{ padding: '4px 8px', color: '#6b7280', textAlign: 'left' }}>Year</th>
                                                                <th style={{ padding: '4px 8px', color: '#10b981', textAlign: 'center' }}>Optimistic</th>
                                                                <th style={{ padding: '4px 8px', color: '#f59e0b', textAlign: 'center' }}>Business as Usual</th>
                                                                <th style={{ padding: '4px 8px', color: '#ef4444', textAlign: 'center' }}>Pessimistic</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {Object.entries(s.projections).map(([year, vals]) => (
                                                                <tr key={year} style={{ borderTop: '1px solid #3a3a3a' }}>
                                                                    <td style={{ padding: '4px 8px', color: '#d1d5db', fontWeight: '600' }}>{year}</td>
                                                                    <td style={{ padding: '4px 8px', color: '#10b981', textAlign: 'center' }}>{vals.optimistic}</td>
                                                                    <td style={{ padding: '4px 8px', color: '#f59e0b', textAlign: 'center' }}>{vals.business_as_usual}</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ef4444', textAlign: 'center' }}>{vals.pessimistic}</td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                ) : (
                                                    <div style={{ fontSize: '11px', color: '#6b7280' }}>No WRI projection data available for this basin.</div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {message.extractedData && (
                                    <div style={{ marginTop: '12px', padding: '16px', background: '#2a2a2a', border: '1px solid #3a3a3a', borderRadius: '8px' }}>
                                        {message.extractedData.bills ? (
                                            // Multiple utility bills view
                                            <>
                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Summary:
                                                </h4>
                                                <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse', marginBottom: '20px' }}>
                                                    <tbody>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Facilities:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.summary?.total_facilities}
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Water Volume:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.summary?.total_water_volume_gallons?.toLocaleString()} gallons
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Cost:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                ${message.extractedData.summary?.total_cost?.toLocaleString()}
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Average Cost per 1,000 gal:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                ${message.extractedData.summary?.average_cost_per_1000_gal}
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>

                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Individual Bills ({message.extractedData.water_bills_found} water bills found):
                                                </h4>
                                                {message.extractedData.bills.map((bill, idx) => (
                                                    <div key={idx} style={{ marginBottom: '16px', padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa', marginBottom: '8px' }}>
                                                            {bill.facility_name} - {bill.bill_id}
                                                        </div>
                                                        <table style={{ width: '100%', fontSize: '12px' }}>
                                                            <tbody>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Water Volume:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        {bill.water_volume_gallons.toLocaleString()} gal
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Total Cost:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        ${bill.total_cost.toLocaleString()}
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Cost/1,000 gal:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        ${bill.cost_per_1000_gal}
                                                                    </td>
                                                                </tr>
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                ))}
                                            </>
                                        ) : message.extractedData.meters ? (
                                            // Meter data view
                                            <>
                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Summary:
                                                </h4>
                                                <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse', marginBottom: '20px' }}>
                                                    <tbody>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Records:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.total_records}
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Meters Tracked:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.meters_tracked}
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Consumption:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.summary?.total_consumption?.toLocaleString()} gallons
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Facilities:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.facilities}
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>

                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Individual Meters ({message.extractedData.meters_tracked} meters):
                                                </h4>
                                                {message.extractedData.meters.map((meter, idx) => (
                                                    <div key={idx} style={{ marginBottom: '16px', padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa', marginBottom: '4px' }}>
                                                            {meter.meter_id} - {meter.location}
                                                        </div>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px' }}>
                                                            Type: {meter.meter_type} | Facility: {meter.facility_id}
                                                        </div>
                                                        <table style={{ width: '100%', fontSize: '12px' }}>
                                                            <tbody>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Consumption:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right', fontWeight: '600' }}>
                                                                        {meter.consumption.toLocaleString()} gal
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Readings:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        {meter.first_reading.toLocaleString()} → {meter.last_reading.toLocaleString()}
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Avg Flow Rate:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        {meter.avg_flow_rate_gpm} GPM
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Avg Temperature:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        {meter.avg_temperature_c}°C
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Status:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#10b981', textAlign: 'right', fontWeight: '600' }}>
                                                                        {meter.status}
                                                                    </td>
                                                                </tr>
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                ))}
                                            </>
                                        ) : message.extractedData.facilities ? (
                                            // Facility info view
                                            <>
                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Summary:
                                                </h4>
                                                <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse', marginBottom: '20px' }}>
                                                    <tbody>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Facilities:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.total_facilities}
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Employees:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.summary?.total_employees?.toLocaleString()}
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Square Footage:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.summary?.total_square_footage?.toLocaleString()} sq ft
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Annual Revenue:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                ${message.extractedData.summary?.total_annual_revenue_usd?.toLocaleString()}
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>

                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Facilities ({message.extractedData.total_facilities}):
                                                </h4>
                                                {message.extractedData.facilities.map((facility, idx) => (
                                                    <div key={idx} style={{ marginBottom: '16px', padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa', marginBottom: '4px' }}>
                                                            {facility.facility_name}
                                                        </div>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px' }}>
                                                            {facility.facility_type} | {facility.industry_type} | ID: {facility.facility_id}
                                                        </div>
                                                        <table style={{ width: '100%', fontSize: '12px' }}>
                                                            <tbody>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Address:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        {facility.address.city}, {facility.address.state}
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Employees:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right', fontWeight: '600' }}>
                                                                        {facility.employees.toLocaleString()}
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Square Footage:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        {facility.square_footage.toLocaleString()} sq ft
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Annual Revenue:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        ${facility.annual_revenue_usd.toLocaleString()}
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Production Capacity:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#10b981', textAlign: 'right', fontWeight: '600' }}>
                                                                        {facility.production_capacity.value.toLocaleString()} {facility.production_capacity.unit}
                                                                    </td>
                                                                </tr>
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                ))}
                                            </>
                                        ) : message.extractedData.suppliers ? (
                                            // Supplier list view
                                            <>
                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Summary:
                                                </h4>
                                                <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse', marginBottom: '20px' }}>
                                                    <tbody>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Suppliers:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.total_suppliers}
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Annual Spend:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                ${message.extractedData.summary?.total_annual_spend_usd?.toLocaleString()}
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Water Intensity:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.summary?.total_water_intensity?.toLocaleString()}
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Categories:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.summary?.categories?.length}
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>

                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Suppliers ({message.extractedData.total_suppliers}):
                                                </h4>
                                                {message.extractedData.suppliers.map((supplier, idx) => (
                                                    <div key={idx} style={{ marginBottom: '16px', padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa', marginBottom: '4px' }}>
                                                            {supplier.supplier_name}
                                                        </div>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px' }}>
                                                            {supplier.material_category} | {supplier.location.city}, {supplier.location.country} | ID: {supplier.supplier_id}
                                                        </div>
                                                        <table style={{ width: '100%', fontSize: '12px' }}>
                                                            <tbody>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Annual Spend:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right', fontWeight: '600' }}>
                                                                        ${supplier.annual_spend_usd.toLocaleString()}
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Water Intensity Factor:</td>
                                                                    <td style={{ padding: '4px 8px', color: supplier.water_intensity_factor > 200000 ? '#ef4444' : supplier.water_intensity_factor > 150000 ? '#f59e0b' : '#10b981', textAlign: 'right', fontWeight: '600' }}>
                                                                        {supplier.water_intensity_factor.toLocaleString()}
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Risk Level:</td>
                                                                    <td style={{ padding: '4px 8px', textAlign: 'right', fontWeight: '600', color: supplier.water_intensity_factor > 200000 ? '#ef4444' : supplier.water_intensity_factor > 150000 ? '#f59e0b' : '#10b981' }}>
                                                                        {supplier.water_intensity_factor > 200000 ? 'High' : supplier.water_intensity_factor > 150000 ? 'Medium' : 'Low'}
                                                                    </td>
                                                                </tr>
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                ))}
                                            </>
                                        ) : message.extractedData.permits ? (
                                            // Discharge report view
                                            <>
                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Summary:
                                                </h4>
                                                <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse', marginBottom: '20px' }}>
                                                    <tbody>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Total Permits:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.total_permits}
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Parameters Tested:</td>
                                                            <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                {message.extractedData.summary?.total_parameters_tested}
                                                            </td>
                                                        </tr>
                                                        <tr style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Passed Parameters:</td>
                                                            <td style={{ padding: '8px 12px', color: '#10b981', fontWeight: '600', textAlign: 'right' }}>
                                                                {message.extractedData.summary?.passed_parameters}
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td style={{ padding: '8px 12px', color: '#9ca3af' }}>Overall Compliance Rate:</td>
                                                            <td style={{ padding: '8px 12px', fontWeight: '600', textAlign: 'right', color: message.extractedData.summary?.overall_compliance_rate >= 95 ? '#10b981' : message.extractedData.summary?.overall_compliance_rate >= 80 ? '#f59e0b' : '#ef4444' }}>
                                                                {message.extractedData.summary?.overall_compliance_rate}%
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>

                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Permits ({message.extractedData.total_permits}):
                                                </h4>
                                                {message.extractedData.permits.map((permit, idx) => (
                                                    <div key={idx} style={{ marginBottom: '16px', padding: '12px', background: '#1a1a1a', borderRadius: '6px', border: '1px solid #3a3a3a' }}>
                                                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#60a5fa', marginBottom: '4px' }}>
                                                            {permit.permit_id} - {permit.outfall_id}
                                                        </div>
                                                        <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '8px' }}>
                                                            {permit.issuing_authority} | Valid: {permit.effective_date} to {permit.expiration_date}
                                                        </div>
                                                        <table style={{ width: '100%', fontSize: '12px', marginBottom: '12px' }}>
                                                            <tbody>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Lab:</td>
                                                                    <td style={{ padding: '4px 8px', color: '#ffffff', textAlign: 'right' }}>
                                                                        {permit.lab_name}
                                                                    </td>
                                                                </tr>
                                                                <tr>
                                                                    <td style={{ padding: '4px 8px', color: '#9ca3af' }}>Compliance Rate:</td>
                                                                    <td style={{ padding: '4px 8px', textAlign: 'right', fontWeight: '600', color: permit.compliance_rate >= 95 ? '#10b981' : permit.compliance_rate >= 80 ? '#f59e0b' : '#ef4444' }}>
                                                                        {permit.compliance_rate}% ({permit.passed_parameters}/{permit.total_parameters})
                                                                    </td>
                                                                </tr>
                                                            </tbody>
                                                        </table>

                                                        <div style={{ fontSize: '11px', fontWeight: '600', color: '#9ca3af', marginBottom: '6px' }}>
                                                            Parameters Tested:
                                                        </div>
                                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                                                            {permit.parameters.map((param, pidx) => (
                                                                <div key={pidx} style={{ padding: '6px 8px', background: '#2a2a2a', borderRadius: '4px', border: `1px solid ${param.compliance_status.toLowerCase() === 'pass' ? '#10b981' : '#ef4444'}` }}>
                                                                    <div style={{ fontSize: '11px', fontWeight: '600', color: '#ffffff' }}>
                                                                        {param.parameter}
                                                                    </div>
                                                                    <div style={{ fontSize: '10px', color: '#9ca3af', marginTop: '2px' }}>
                                                                        Limit: {param.limit_value} {param.limit_unit}
                                                                    </div>
                                                                    <div style={{ fontSize: '10px', color: param.compliance_status.toLowerCase() === 'pass' ? '#10b981' : '#ef4444', marginTop: '2px', fontWeight: '600' }}>
                                                                        Sample: {param.sample_value} - {param.compliance_status.toUpperCase()}
                                                                    </div>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                ))}
                                            </>
                                        ) : (
                                            // Single record view
                                            <>
                                                <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: '#ffffff' }}>
                                                    Extracted Data:
                                                </h4>
                                                <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse' }}>
                                                    <tbody>
                                                        {Object.entries(message.extractedData).map(([key, value]) => (
                                                            <tr key={key} style={{ borderBottom: '1px solid #3a3a3a' }}>
                                                                <td style={{ padding: '8px 12px', color: '#9ca3af', textAlign: 'left' }}>
                                                                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                                                                </td>
                                                                <td style={{ padding: '8px 12px', color: '#ffffff', fontWeight: '500', textAlign: 'right' }}>
                                                                    {typeof value === 'object' ? JSON.stringify(value) : value}
                                                                </td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </>
                                        )}
                                    </div>
                                )}

                                {message.options && message.options.length > 0 && (
                                    <div className="message-options">
                                        {message.options.map((option) => (
                                            <button
                                                key={option.id}
                                                className="option-button"
                                                onClick={() => handleOptionClick(option.id)}
                                            >
                                                <div className="option-text">
                                                    <div className="option-label">{option.label}</div>
                                                    {option.description && (
                                                        <div className="option-description">{option.description}</div>
                                                    )}
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {isTyping && (
                        <div className="message-wrapper">
                            <div className="message-avatar bot">💧</div>
                            <div className="message-content">
                                <div className="message-bubble bot">
                                    <div className="typing-indicator">
                                        <div className="typing-dot"></div>
                                        <div className="typing-dot"></div>
                                        <div className="typing-dot"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                <div className="chat-input-container">
                    <div className="chat-input-wrapper">
                        <input
                            ref={inputRef}
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage(inputValue)}
                            placeholder="Type your message..."
                            className="chat-input"
                        />
                        <button
                            onClick={() => handleSendMessage(inputValue)}
                            disabled={!inputValue.trim()}
                            className="send-button"
                        >
                            Send
                        </button>
                    </div>
                </div>
            </div>

            {/* Persistent right sidebar */}
            <aside className="chat-sidebar">
                <div className="sidebar-title">Quick Actions</div>
                {SIDEBAR_ITEMS.map((item) => (
                    <button
                        key={item.id}
                        className="sidebar-item"
                        onClick={() => handleOptionClick(item.id)}
                        title={item.label}
                    >
                        <span className="sidebar-icon">{item.icon}</span>
                        <span className="sidebar-label">{item.label}</span>
                    </button>
                ))}
            </aside>
        </div>
    );
};

export default ChatInterface;
