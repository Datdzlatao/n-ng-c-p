import React from 'react';

export function Button({ 
  children, 
  variant = 'primary', 
  size = 'md', 
  className = '', 
  loading = false, 
  ...props 
}) {
  const baseStyles = 'inline-flex items-center justify-center font-semibold rounded-xl transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-500/20',
    outline: 'bg-transparent border border-white/10 hover:border-white/20 text-gray-200 hover:text-white',
    success: 'bg-green-600 hover:bg-green-500 text-white',
    danger: 'bg-red-600 hover:bg-red-500 text-white',
    ghost: 'hover:bg-white/5 text-gray-300 hover:text-white',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs gap-1.5',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-6 py-3 text-base gap-2.5',
  };

  return (
    <button 
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading ? (
        <span className="inline-block w-4 h-4 border-2 border-current border-r-transparent rounded-full animate-spin" />
      ) : null}
      {children}
    </button>
  );
}
