import React, { useState, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'react-hot-toast';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const UploadWidget = ({ uploadType, sessionId, onUploadComplete, onCancel }) => {
    const [isDragging, setIsDragging] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [selectedFile, setSelectedFile] = useState(null);

    const handleDragOver = useCallback((e) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e) => {
        e.preventDefault();
        setIsDragging(false);

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    }, []);

    const handleFileSelect = (file) => {
        // Validate file type
        const allowedTypes = ['application/pdf', 'text/csv', 'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/png', 'image/jpeg', 'image/jpg'];

        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|csv|xlsx?|png|jpe?g)$/i)) {
            toast.error('Invalid file type. Please upload PDF, CSV, Excel, or Image files.');
            return;
        }

        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            toast.error('File size exceeds 10MB limit.');
            return;
        }

        setSelectedFile(file);
    };

    const handleUpload = async () => {
        if (!selectedFile) {
            toast.error('Please select a file first.');
            return;
        }

        setIsUploading(true);
        setUploadProgress(0);

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('file_type', uploadType);
        formData.append('user_id', 'demo');
        formData.append('metadata', JSON.stringify({ session_id: sessionId }));

        try {
            const response = await axios.post(`${API_URL}/api/upload/`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
                onUploadProgress: (progressEvent) => {
                    const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                    setUploadProgress(progress);
                },
            });

            setIsUploading(false);
            toast.success('File uploaded and processed successfully!');

            // Call the completion callback with the response data
            if (onUploadComplete) {
                onUploadComplete(response.data);
            }

            // Reset state
            setSelectedFile(null);
            setUploadProgress(0);

        } catch (error) {
            setIsUploading(false);
            console.error('Upload error:', error);
            toast.error(error.response?.data?.detail || 'Failed to upload file. Please try again.');
        }
    };

    const getFileTypeLabel = () => {
        const labels = {
            utility_bills: 'Utility Bill',
            meter_readings: 'Meter Reading',
            facility_info: 'Facility Information',
            supplier_list: 'Supplier List',
            discharge_reports: 'Discharge Report'
        };
        return labels[uploadType] || 'File';
    };

    const getAcceptedFormats = () => {
        const formats = {
            utility_bills: '.pdf, .csv, .xlsx, .xls',
            meter_readings: '.csv, .xlsx, .xls',
            facility_info: '.pdf, .csv, .xlsx, .xls',
            supplier_list: '.csv, .xlsx, .xls',
            discharge_reports: '.pdf, .csv, .xlsx, .xls'
        };
        return formats[uploadType] || '.pdf, .csv, .xlsx, .xls';
    };

    return (
        <div className="space-y-4">
            {/* Upload Area */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`upload-zone border-2 border-dashed rounded-xl p-8 text-center transition-all ${isDragging
                        ? 'border-blue-500 bg-blue-500/10 scale-105'
                        : 'border-gray-700 hover:border-blue-500/50'
                    }`}
            >
                <div className="flex flex-col items-center space-y-4">
                    <div className="w-16 h-16 rounded-full bg-gradient-to-r from-blue-500 to-teal-500 flex items-center justify-center">
                        <span className="text-3xl">📤</span>
                    </div>

                    <div>
                        <h3 className="text-lg font-semibold text-gray-100 mb-2">
                            Upload {getFileTypeLabel()}
                        </h3>
                        <p className="text-sm text-gray-400 mb-4">
                            Drag and drop your file here, or click to browse
                        </p>
                        <p className="text-xs text-gray-500">
                            Accepted formats: {getAcceptedFormats()} (Max 10MB)
                        </p>
                    </div>

                    <input
                        type="file"
                        id="file-upload"
                        className="hidden"
                        accept={getAcceptedFormats()}
                        onChange={(e) => e.target.files.length > 0 && handleFileSelect(e.target.files[0])}
                    />

                    <label
                        htmlFor="file-upload"
                        className="px-6 py-3 bg-gradient-to-r from-blue-600 to-teal-600 hover:from-blue-700 hover:to-teal-700 rounded-lg cursor-pointer transition-all hover:scale-105 font-medium"
                    >
                        Browse Files
                    </label>
                </div>
            </div>

            {/* Selected File */}
            {selectedFile && (
                <div className="glass rounded-lg p-4 border border-gray-700">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                                <span className="text-xl">📄</span>
                            </div>
                            <div>
                                <div className="font-medium text-gray-100">{selectedFile.name}</div>
                                <div className="text-sm text-gray-400">
                                    {(selectedFile.size / 1024).toFixed(2)} KB
                                </div>
                            </div>
                        </div>

                        {!isUploading && (
                            <button
                                onClick={() => setSelectedFile(null)}
                                className="text-gray-400 hover:text-red-400 transition-colors"
                            >
                                <span className="text-xl">✕</span>
                            </button>
                        )}
                    </div>

                    {/* Upload Progress */}
                    {isUploading && (
                        <div className="mt-4">
                            <div className="flex items-center justify-between text-sm mb-2">
                                <span className="text-gray-400">Uploading and processing...</span>
                                <span className="text-blue-400 font-medium">{uploadProgress}%</span>
                            </div>
                            <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
                                <div
                                    className="bg-gradient-to-r from-blue-500 to-teal-500 h-full transition-all duration-300 ease-out"
                                    style={{ width: `${uploadProgress}%` }}
                                ></div>
                            </div>
                            <div className="mt-2 text-xs text-gray-500 text-center">
                                Using Gemini AI to extract and analyze data...
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-end space-x-3">
                <button
                    onClick={onCancel}
                    disabled={isUploading}
                    className="px-6 py-3 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-800 disabled:cursor-not-allowed rounded-lg transition-colors font-medium"
                >
                    Cancel
                </button>
                <button
                    onClick={handleUpload}
                    disabled={!selectedFile || isUploading}
                    className="px-6 py-3 bg-gradient-to-r from-blue-600 to-teal-600 hover:from-blue-700 hover:to-teal-700 disabled:from-gray-700 disabled:to-gray-700 disabled:cursor-not-allowed rounded-lg transition-all hover:scale-105 disabled:hover:scale-100 font-medium"
                >
                    {isUploading ? 'Processing...' : 'Upload & Process'}
                </button>
            </div>

            {/* Info Box */}
            <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                    <span className="text-xl">💡</span>
                    <div className="flex-1">
                        <h4 className="font-medium text-blue-300 mb-1">AI-Powered Processing</h4>
                        <p className="text-sm text-gray-400">
                            Your file will be processed using Gemini AI to extract water usage data,
                            meter readings, pollutant levels, and other relevant information.
                            All data is securely stored in MongoDB for future analysis.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UploadWidget;