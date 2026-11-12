import React from 'react';
import { X } from 'lucide-react';

export function Modal({ isOpen, onClose, title, subtitle, children, maxWidth = 'max-w-md' }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fadeIn">
      <div className={`bg-[#1a1d27] border border-white/10 w-full ${maxWidth} rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]`}>
        {title && (
          <div className="p-4 border-b border-white/10 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-white text-base">{title}</h3>
              {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
            </div>
            <button 
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-white/5 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        )}
        <div className="p-4 overflow-y-auto flex-1">
          {children}
        </div>
      </div>
    </div>
  );
}
