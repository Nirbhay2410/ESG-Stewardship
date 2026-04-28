import React from 'react';

const MessageBubble = ({ message, onOptionClick }) => {
    const isUser = message.role === 'user';

    const renderContent = () => {
        if (message.type === 'dashboard' && message.data) {
            return (
                <div className="space-y-4">
                    <p className="text-gray-100 mb-4">{message.content}</p>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 gap-3">
                        {message.data.summary_cards?.map((card, index) => (
                            <div key={index} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-2xl">{card.icon}</span>
                                    {card.trend && (
                                        <span className={`text-xs ${card.trend.startsWith('+') ? 'text-red-400' : 'text-green-400'}`}>
                                            {card.trend}
                                        </span>
                                    )}
                                </div>
                                <div className="text-sm text-gray-400">{card.title}</div>
                                <div className="text-xl font-bold text-gray-100">{card.value}</div>
                                {card.percentage && (
                                    <div className="text-xs text-gray-500 mt-1">{card.percentage}</div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            );
        }

        if (message.type === 'risk_assessment' && message.data) {
            return (
                <div className="space-y-4">
                    <p className="text-gray-100 mb-4">{message.content}</p>

                    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                        <div className="flex items-center justify-between mb-3">
                            <h3 className="font-semibold text-gray-100">
                                {message.data.location?.nearest_data_point?.basin_name || 'Facility Assessment'}
                            </h3>
                            <span className={`px-3 py-1 rounded-full text-sm font-medium ${message.data.overall_risk_score >= 4 ? 'bg-red-900/30 text-red-400' :
                                message.data.overall_risk_score >= 3 ? 'bg-orange-900/30 text-orange-400' :
                                    message.data.overall_risk_score >= 2 ? 'bg-yellow-900/30 text-yellow-400' :
                                        'bg-green-900/30 text-green-400'
                                }`}>
                                {message.data.risk_level}
                            </span>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-gray-400">Overall Risk Score</span>
                                <span className="text-lg font-bold text-gray-100">{message.data.overall_risk_score}/5.0</span>
                            </div>

                            {message.data.risk_indicators && Object.entries(message.data.risk_indicators).slice(0, 3).map(([key, value]) => (
                                <div key={key} className="flex justify-between items-center">
                                    <span className="text-sm text-gray-400">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                                    <span className="text-sm text-gray-100">{value.score}/5.0</span>
                                </div>
                            ))}
                        </div>

                        {message.data.key_findings && (
                            <div className="mt-4 pt-4 border-t border-gray-700">
                                <h4 className="text-sm font-semibold text-gray-300 mb-2">Key Findings:</h4>
                                <ul className="space-y-1">
                                    {message.data.key_findings.slice(0, 3).map((finding, index) => (
                                        <li key={index} className="text-sm text-gray-400">• {finding}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                </div>
            );
        }

        if (message.type === 'efficiency_opportunities' && message.data) {
            return (
                <div className="space-y-4">
                    <p className="text-gray-100 mb-4">{message.content}</p>

                    <div className="space-y-3">
                        {message.data.opportunities?.slice(0, 5).map((opp, index) => (
                            <div key={index} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700 hover:border-blue-500 transition-colors cursor-pointer">
                                <div className="flex items-start justify-between mb-2">
                                    <div className="flex-1">
                                        <div className="flex items-center space-x-2 mb-1">
                                            <span className="text-lg">{index === 0 ? '🔧' : index === 1 ? '💧' : index === 2 ? '❄️' : index === 3 ? '♻️' : '🌱'}</span>
                                            <h4 className="font-semibold text-gray-100">{opp.name}</h4>
                                        </div>
                                        <p className="text-sm text-gray-400">{opp.description}</p>
                                    </div>
                                    <span className={`px-2 py-1 rounded text-xs font-medium ${opp.priority === 'Immediate' ? 'bg-red-900/30 text-red-400' :
                                        opp.priority === 'High' ? 'bg-orange-900/30 text-orange-400' :
                                            'bg-blue-900/30 text-blue-400'
                                        }`}>
                                        {opp.priority}
                                    </span>
                                </div>

                                <div className="grid grid-cols-3 gap-3 mt-3">
                                    <div>
                                        <div className="text-xs text-gray-500">Savings</div>
                                        <div className="text-sm font-medium text-green-400">{opp.savings?.water?.toLocaleString()} gal/yr</div>
                                    </div>
                                    <div>
                                        <div className="text-xs text-gray-500">Cost</div>
                                        <div className="text-sm font-medium text-gray-300">${opp.implementation_cost?.toLocaleString()}</div>
                                    </div>
                                    <div>
                                        <div className="text-xs text-gray-500">Payback</div>
                                        <div className="text-sm font-medium text-blue-400">{opp.payback_months} months</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {message.data.total_potential_savings && (
                        <div className="bg-gradient-to-r from-green-900/30 to-blue-900/30 rounded-lg p-4 border border-green-700/50">
                            <div className="text-sm text-gray-300 mb-2">Total Potential Savings:</div>
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="text-2xl font-bold text-green-400">{(message.data.total_potential_savings / 1000000).toFixed(2)}M gal/year</div>
                                    <div className="text-sm text-gray-400">Portfolio Payback: {message.data.average_payback?.toFixed(1)} years</div>
                                </div>
                                <div className="text-right">
                                    <div className="text-xl font-bold text-green-400">${message.data.total_investment?.toLocaleString()}</div>
                                    <div className="text-sm text-gray-400">Total Investment</div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            );
        }

        if (message.type === 'upload_success' && message.data) {
            return (
                <div className="space-y-3">
                    <p className="text-gray-100">{message.content}</p>

                    {message.data.extracted_data && (
                        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                            <h4 className="text-sm font-semibold text-gray-300 mb-3">Extracted Data:</h4>
                            <div className="space-y-2">
                                {Object.entries(message.data.extracted_data).slice(0, 8).map(([key, value]) => (
                                    <div key={key} className="flex justify-between items-center text-sm">
                                        <span className="text-gray-400">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</span>
                                        <span className="text-gray-100 font-medium">{typeof value === 'object' ? JSON.stringify(value) : value}</span>
                                    </div>
                                ))}
                            </div>

                            {message.data.confidence_score && (
                                <div className="mt-3 pt-3 border-t border-gray-700">
                                    <div className="flex items-center justify-between">
                                        <span className="text-sm text-gray-400">Confidence Score:</span>
                                        <span className="text-sm font-medium text-green-400">{(message.data.confidence_score * 100).toFixed(0)}%</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            );
        }

        // Default text content
        return <p className="text-gray-100 whitespace-pre-wrap">{message.content}</p>;
    };

    return (
        <div className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
            {/* Avatar */}
            {!isUser && (
                <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm">💧</span>
                </div>
            )}

            {/* Message Content */}
            <div className={`flex-1 max-w-3xl ${isUser ? 'flex justify-end' : ''}`}>
                <div className={`rounded-lg px-4 py-3 ${isUser
                    ? 'bg-blue-600 text-white'
                    : 'bg-[#2d2d2d] text-white border border-gray-700'
                    }`}>
                    {renderContent()}

                    {/* Options */}
                    {message.options && message.options.length > 0 && (
                        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
                            {message.options.map((option) => (
                                <button
                                    key={option.id}
                                    onClick={() => onOptionClick(option.id)}
                                    className="text-left px-4 py-3 bg-[#3d3d3d] hover:bg-[#4d4d4d] border border-gray-600 hover:border-blue-500 rounded-lg transition-colors flex items-center space-x-3"
                                >
                                    <span className="text-xl">{option.label.split(' ')[0]}</span>
                                    <div className="flex-1">
                                        <div className="font-medium text-white text-sm">{option.label.substring(option.label.indexOf(' ') + 1)}</div>
                                        {option.description && (
                                            <div className="text-xs text-gray-400 mt-0.5">{option.description}</div>
                                        )}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Timestamp */}
                    <div className={`text-xs mt-2 ${isUser ? 'text-blue-200' : 'text-gray-500'}`}>
                        {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                </div>
            </div>

            {/* User Avatar */}
            {isUser && (
                <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm">👤</span>
                </div>
            )}
        </div>
    );
};

export default MessageBubble;