"""
Lazy import utilities for performance optimization.
"""
import importlib
import sys
from typing import Dict, List, Any, Optional
from functools import wraps
import time

# Global state for lazy loading
_lazy_modules = {}
_loaded_modules = set()
_import_stats = {
    'total_imports': 0,
    'lazy_imports': 0,
    'load_times': {}
}

def lazy_import(module_name: str, package: Optional[str] = None):
    """
    Lazily import a module when first accessed.
    
    Args:
        module_name: Name of the module to import
        package: Package name for relative imports
        
    Returns:
        Module proxy that loads on first access
    """
    if module_name in _lazy_modules:
        return _lazy_modules[module_name]
    
    class LazyModule:
        def __init__(self, name: str, pkg: Optional[str] = None):
            self._name = name
            self._package = pkg
            self._module = None
            
        def _load_module(self):
            if self._module is None:
                start_time = time.time()
                try:
                    self._module = importlib.import_module(self._name, self._package)
                    _loaded_modules.add(self._name)
                    load_time = time.time() - start_time
                    _import_stats['load_times'][self._name] = load_time
                    _import_stats['lazy_imports'] += 1
                except ImportError as e:
                    # Return a dummy module to prevent repeated import attempts
                    self._module = type('DummyModule', (), {})()
                    raise e
            return self._module
            
        def __getattr__(self, name):
            module = self._load_module()
            return getattr(module, name)
            
        def __call__(self, *args, **kwargs):
            module = self._load_module()
            return module(*args, **kwargs)
    
    proxy = LazyModule(module_name, package)
    _lazy_modules[module_name] = proxy
    return proxy

def preload_essential_modules():
    """Preload essential modules for better performance."""
    essential_modules = [
        'streamlit',
        'docx',
        'io',
        'json',
        'logging',
        'typing'
    ]
    
    for module_name in essential_modules:
        try:
            importlib.import_module(module_name)
            _loaded_modules.add(module_name)
        except ImportError:
            pass  # Module not available
    
    _import_stats['total_imports'] = len(_loaded_modules)

def get_lazy_module_stats() -> Dict[str, Any]:
    """Get statistics about lazy module loading."""
    return {
        'total_imports': _import_stats['total_imports'],
        'lazy_imports': _import_stats['lazy_imports'],
        'loaded_count': len(_loaded_modules),
        'loaded_modules': list(_loaded_modules),
        'load_times': _import_stats['load_times'].copy(),
        'average_load_time': sum(_import_stats['load_times'].values()) / max(1, len(_import_stats['load_times']))
    }

def clear_lazy_cache():
    """Clear the lazy import cache."""
    global _lazy_modules, _loaded_modules, _import_stats
    _lazy_modules.clear()
    _loaded_modules.clear()
    _import_stats = {
        'total_imports': 0,
        'lazy_imports': 0,
        'load_times': {}
    }

def performance_import(func):
    """Decorator to track import performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        func_name = getattr(func, '__name__', 'unknown')
        _import_stats['load_times'][func_name] = end_time - start_time
        
        return result
    return wrapper
