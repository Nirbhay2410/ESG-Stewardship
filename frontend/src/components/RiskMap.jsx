import React from 'react';

const RiskMap = ({ sessionId }) => {
    return (
        <div className="p-6">
            <h2 className="text-2xl font-bold mb-6">Water Risk Map</h2>
            <p className="text-gray-400">Interactive risk map coming soon...</p>
            <p className="text-sm text-gray-500 mt-2">
                This will display an interactive map showing water stress levels
                for your facilities and suppliers using WRI Aqueduct data.
            </p>
        </div>
    );
};

export default RiskMap;