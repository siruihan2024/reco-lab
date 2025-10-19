import { useState, useRef, useEffect, useCallback } from 'react';
import { Search, RefreshCw, BarChart3, Sparkles, TrendingUp, X, CheckCircle2, Database, FolderOpen, Image, Mic, ArrowRight, Zap } from 'lucide-react';

interface Product {
  id: string;
  name: string;
  score?: number;
}

interface RecommendResponse {
  anchor: Product;
  items: Product[];
  understanding?: string;
  query?: string;
  image_filename?: string;
  image_size_kb?: number;
  transcription?: string;
  language?: string;
  duration?: number;
}

interface StatsData {
  num_products: number;
  top_categories: [string, number][];
  category_mapper: {
    total_cached: number;
    valid_cached: number;
    expired_cached: number;
    cache_file: string;
  };
}

function App() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecommendResponse | null>(null);
  const [error, setError] = useState('');
  const [adminLoading, setAdminLoading] = useState<'reload' | 'stats' | null>(null);
  const [showStatsModal, setShowStatsModal] = useState(false);
  const [statsData, setStatsData] = useState<StatsData | null>(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const imageInputRef = useRef<HTMLInputElement>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);
  const [uploadType, setUploadType] = useState<'image' | 'audio' | null>(null);

  const [suggestions, setSuggestions] = useState<Product[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const cacheRef = useRef<Map<string, Product[]>>(new Map());
  const [perfStats, setPerfStats] = useState({ requests: 0, cacheHits: 0, debounced: 0 });

  const handleRecommend = async () => {
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await fetch('/recommend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          top_k: topK,
        }),
      });

      if (!response.ok) {
        throw new Error('Request failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleAdminAction = async (action: 'reload' | 'stats') => {
    setAdminLoading(action);
    setError('');

    try {
      const response = await fetch(`/admin/${action}`, {
        method: action === 'reload' ? 'POST' : 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`${action} operation failed`);
      }

      const data = await response.json();

      if (action === 'reload') {
        setSuccessMessage(`${data.num_products || 0} products loaded successfully`);
        setShowSuccessModal(true);
      } else {
        setStatsData(data);
        setShowStatsModal(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed');
    } finally {
      setAdminLoading(null);
    }
  };

  const fetchSuggestions = useCallback(async (searchQuery: string) => {
    const trimmed = searchQuery.trim();

    if (trimmed.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const cached = cacheRef.current.get(trimmed);
    if (cached) {
      setSuggestions(cached);
      setShowSuggestions(cached.length > 0);
      setPerfStats(prev => ({ ...prev, cacheHits: prev.cacheHits + 1 }));
      return;
    }

    setSuggestionLoading(true);
    setPerfStats(prev => ({ ...prev, requests: prev.requests + 1 }));

    try {
      const response = await fetch('/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmed, top_k: 8 }),
      });

      if (response.ok) {
        const data = await response.json();
        const items = data.items || [];

        cacheRef.current.set(trimmed, items);
        if (cacheRef.current.size > 100) {
          const firstKey = cacheRef.current.keys().next().value;
          cacheRef.current.delete(firstKey);
        }

        setSuggestions(items);
        setShowSuggestions(items.length > 0);
      }
    } catch (err) {
      setSuggestions([]);
      setShowSuggestions(false);
    } finally {
      setSuggestionLoading(false);
    }
  }, []);

  const handleQueryChange = (value: string) => {
    setQuery(value);
    setSelectedIndex(-1);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
      setPerfStats(prev => ({ ...prev, debounced: prev.debounced + 1 }));
    }

    debounceTimerRef.current = setTimeout(() => {
      fetchSuggestions(value);
    }, 300);
  };
 
  const handleSuggestionSelect = (suggestion: Product) => {
    setQuery(suggestion.name);
    setShowSuggestions(false);
    setSuggestions([]);
    setSelectedIndex(-1);
    searchInputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showSuggestions && suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : prev));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => (prev > 0 ? prev - 1 : -1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleSuggestionSelect(suggestions[selectedIndex]);
        } else if (!loading) {
          setShowSuggestions(false);
          handleRecommend();
        }
      } else if (e.key === 'Escape') {
        setShowSuggestions(false);
      }
    } else if (e.key === 'Enter' && !loading) {
      handleRecommend();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading) {
      handleRecommend();
    }
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        searchInputRef.current &&
        !searchInputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const handleFileUpload = async (file: File, type: 'image' | 'audio') => {
    setLoading(true);
    setError('');
    setResult(null);
    setUploadType(type);

    try {
      const formData = new FormData();
      formData.append(type, file);
      formData.append('top_k', topK.toString());

      const response = await fetch(`/recommend/${type === 'audio' ? 'voice' : 'image'}`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
      setUploadType(null);
    }
  };

  
  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const validTypes = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      if (validTypes.includes(fileExt)) {
        handleFileUpload(file, 'image');
      } else {
        setError('Invalid image format. Supported formats: ' + validTypes.join(', '));
      }
    }
    if (imageInputRef.current) imageInputRef.current.value = '';
  };

  const handleAudioSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const validTypes = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.aac', '.wma', '.opus'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      if (validTypes.includes(fileExt)) {
        handleFileUpload(file, 'audio');
      } else {
        setError('Invalid audio format. Supported formats: ' + validTypes.join(', '));
      }
    }
    if (audioInputRef.current) audioInputRef.current.value = '';
  };


  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-medium bg-gradient-to-r from-[#4285F4] via-[#EA4335] to-[#FBBC04] bg-clip-text text-transparent">Product Recommender</span>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => handleAdminAction('reload')}
              disabled={adminLoading !== null}
              className="flex items-center gap-2 px-4 py-2 text-[#4285F4] hover:bg-blue-50 rounded-full transition-colors disabled:opacity-50 text-sm font-medium"
            >
              <RefreshCw className={`w-4 h-4 ${adminLoading === 'reload' ? 'animate-spin' : ''}`} />
              Reload
            </button>
            <button
              onClick={() => handleAdminAction('stats')}
              disabled={adminLoading !== null}
              className="flex items-center gap-2 px-4 py-2 text-[#34A853] hover:bg-green-50 rounded-full transition-colors disabled:opacity-50 text-sm font-medium"
            >
              <BarChart3 className="w-4 h-4" />
              Stats
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-3xl mx-auto px-6 pt-20">
        {/* Search Section */}
        <div className="mb-8">
          <div className="mb-6">
            <div className="flex items-start gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-5 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 z-10" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={query}
                  onChange={(e) => handleQueryChange(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
                  placeholder="Search products"
                  className="w-full pl-14 pr-12 py-4 border border-gray-300 hover:border-gray-400 focus:border-[#4285F4] rounded-full focus:outline-none transition-all duration-200 text-gray-900 placeholder-gray-500 text-base shadow-sm hover:shadow-md focus:shadow-lg"
                  autoComplete="off"
                />

                {suggestionLoading && query.length >= 2 && (
                  <div className="absolute right-5 top-1/2 transform -translate-y-1/2">
                    <RefreshCw className="w-5 h-5 text-[#4285F4] animate-spin" />
                  </div>
                )}

                {showSuggestions && suggestions.length > 0 && (
                  <div
                    ref={suggestionsRef}
                    className="absolute z-50 w-full mt-2 bg-white rounded-2xl shadow-lg border border-gray-200 max-h-96 overflow-y-auto"
                  >
                    <div className="py-2">
                      {suggestions.map((item, index) => (
                        <button
                          key={item.id}
                          onClick={() => handleSuggestionSelect(item)}
                          className={`w-full text-left px-5 py-3 transition-colors flex items-center justify-between group ${
                            index === selectedIndex
                              ? 'bg-gray-100'
                              : 'hover:bg-gray-50'
                          }`}
                        >
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <div className="text-sm text-gray-900 truncate">{item.name}</div>
                            </div>
                          </div>
                          {item.score !== undefined && (
                            <span className="text-xs text-gray-500 ml-3 flex-shrink-0">
                              {(item.score * 100).toFixed(0)}%
                            </span>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <button
                onClick={handleRecommend}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-4 bg-[#4285F4] hover:bg-[#3367D6] text-white rounded-full transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium shadow-sm hover:shadow whitespace-nowrap"
              >
                {loading && !uploadType ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Recommend
                  </>
                )}
              </button>
            </div>

            {/* Secondary Actions - Second row */}
            <div className="flex flex-wrap gap-3 justify-center mt-4">
              <input
                ref={imageInputRef}
                type="file"
                accept=".jpg,.jpeg,.png,.webp,.bmp,.gif"
                onChange={handleImageSelect}
                className="hidden"
              />
              <button
                onClick={() => imageInputRef.current?.click()}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 bg-white hover:bg-red-50 text-[#EA4335] border border-[#EA4335] rounded-full transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium shadow-sm hover:shadow"
              >
                {loading && uploadType === 'image' ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Image className="w-4 h-4" />
                    Upload Image
                  </>
                )}
              </button>

              <input
                ref={audioInputRef}
                type="file"
                accept=".wav,.mp3,.m4a,.ogg,.flac,.aac,.wma,.opus"
                onChange={handleAudioSelect}
                className="hidden"
              />
              <button
                onClick={() => audioInputRef.current?.click()}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 bg-white hover:bg-yellow-50 text-[#FBBC04] border border-[#FBBC04] rounded-full transition-all disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium shadow-sm hover:shadow"
              >
                {loading && uploadType === 'audio' ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Mic className="w-4 h-4" />
                    Upload Audio
                  </>
                )}
              </button>

              <div className="flex items-center gap-2 px-4 py-2.5 bg-white text-[#34A853] border border-[#34A853] rounded-full text-sm shadow-sm font-medium">
                <span>Results</span>
                <input
                  type="number"
                  value={topK}
                  onChange={(e) => setTopK(Math.max(1, parseInt(e.target.value) || 5))}
                  min="1"
                  max="20"
                  className="w-12 px-2 py-1 border border-gray-300 rounded text-center focus:outline-none focus:border-[#4285F4] bg-white"
                />
              </div>
            </div>
          </div>

          {/* Upload Info */}
          {result && (result.understanding || result.transcription) && (
            <div className="mt-6">
              {result.understanding && (
                <div className="bg-green-50 rounded-lg p-4 border-l-4 border-[#34A853] mb-3">
                  <p className="text-sm font-medium text-gray-700 mb-1">Image Understanding</p>
                  <p className="text-gray-900">{result.understanding}</p>
                  {result.image_filename && (
                    <p className="text-xs text-gray-600 mt-2">
                      {result.image_filename} • {result.image_size_kb?.toFixed(2)} KB
                    </p>
                  )}
                </div>
              )}
              {result.transcription && (
                <div className="bg-red-50 rounded-lg p-4 border-l-4 border-[#EA4335]">
                  <p className="text-sm font-medium text-gray-700 mb-1">Audio Transcription</p>
                  <p className="text-gray-900">{result.transcription}</p>
                  <p className="text-xs text-gray-600 mt-2">
                    {result.language} • {result.duration?.toFixed(2)}s
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Error Message show */}
        {error && (
          <div className="bg-red-50 border-l-4 border-[#EA4335] p-4 rounded-lg mb-8">
            <p className="text-gray-800">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-4">
            {/* Anchor Product */}
            <div className="bg-blue-50 rounded-lg p-4 border-l-4 border-[#4285F4]">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-[#4285F4]" />
                <span className="text-xs font-medium text-gray-600 uppercase">Anchor Product</span>
              </div>
              <div className="flex items-center justify-between">
                <p className="text-lg font-medium text-gray-900">{result.anchor.name}</p>
                <span className="text-xs text-gray-500 font-mono bg-white px-3 py-1 rounded-full">
                  {result.anchor.id}
                </span>
              </div>
            </div>

            {/* Recommended Products */}
            <div>
              <h3 className="text-sm font-medium text-gray-600 mb-3 uppercase">Recommended Products</h3>
              <div className="space-y-2">
                {result.items.map((item, index) => {
                  const colors = ['#4285F4', '#EA4335', '#FBBC04', '#34A853'];
                  const color = colors[index % colors.length];
                  return (
                    <div
                      key={item.id}
                      className="bg-white rounded-lg p-4 border border-gray-200 hover:border-gray-300 hover:shadow transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 flex-1">
                          <span
                            className="w-8 h-8 rounded-full flex items-center justify-center font-medium text-white text-sm"
                            style={{ backgroundColor: color }}
                          >
                            {index + 1}
                          </span>
                          <div className="flex-1">
                            <p className="text-sm font-medium text-gray-900">{item.name}</p>
                            <p className="text-xs text-gray-500 mt-0.5">{item.id}</p>
                          </div>
                        </div>
                        <div className="text-sm font-medium text-gray-600">
                          {((item.score || 0) * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!result && !loading && !error && (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-xl font-normal text-gray-700 mb-2">
              Start searching for products
            </h3>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              Enter a product name or upload an image/audio to get recommendations
            </p>
          </div>
        )}
      </div>

      {/* Statistics Modal */}
      {showStatsModal && statsData && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <BarChart3 className="w-5 h-5 text-gray-700" />
                <h2 className="text-lg font-medium text-gray-900">Statistics</h2>
              </div>
              <button
                onClick={() => setShowStatsModal(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors p-2 hover:bg-gray-100 rounded-full"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
              {/* Total Products */}
              <div className="bg-blue-50 rounded-lg p-4 border-l-4 border-[#4285F4] mb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-[#4285F4]" />
                    <span className="text-sm text-gray-600">Total Products</span>
                  </div>
                  <p className="text-2xl font-medium text-gray-900">{statsData.num_products}</p>
                </div>
              </div>

              {/* Top Categories */}
              <div className="mb-4">
                <h3 className="text-sm font-medium text-gray-600 mb-3 uppercase">Top Categories</h3>
                <div className="space-y-2">
                  {statsData.top_categories.map(([category, count], index) => {
                    const percentage = (count / statsData.num_products) * 100;
                    const colors = ['#4285F4', '#EA4335', '#FBBC04', '#34A853'];
                    const color = colors[index % colors.length];
                    return (
                      <div key={index} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span
                              className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-medium"
                              style={{ backgroundColor: color }}
                            >
                              {index + 1}
                            </span>
                            <span className="text-sm font-medium text-gray-900">{category}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-sm font-medium text-gray-900">{count}</span>
                            <span className="text-xs text-gray-500 ml-2">{percentage.toFixed(1)}%</span>
                          </div>
                        </div>
                        <div className="bg-gray-200 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{ width: `${percentage}%`, backgroundColor: color }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Category Cache */}
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 mb-4">
                <h3 className="text-sm font-medium text-gray-600 mb-3 uppercase">Category Cache</h3>
                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div className="text-center p-3 bg-white rounded border border-gray-200">
                    <p className="text-lg font-medium text-gray-900">{statsData.category_mapper.total_cached}</p>
                    <p className="text-xs text-gray-500 mt-1">Total</p>
                  </div>
                  <div className="text-center p-3 bg-white rounded border border-gray-200">
                    <p className="text-lg font-medium text-[#34A853]">{statsData.category_mapper.valid_cached}</p>
                    <p className="text-xs text-gray-500 mt-1">Valid</p>
                  </div>
                  <div className="text-center p-3 bg-white rounded border border-gray-200">
                    <p className="text-lg font-medium text-[#FBBC04]">{statsData.category_mapper.expired_cached}</p>
                    <p className="text-xs text-gray-500 mt-1">Expired</p>
                  </div>
                </div>
                <div className="bg-white rounded p-2 border border-gray-200">
                  <p className="text-xs text-gray-500 mb-1">Cache File</p>
                  <p className="text-xs font-mono text-gray-700 break-all">{statsData.category_mapper.cache_file}</p>
                </div>
              </div>

              {/* Frontend Performance */}
              <div className="bg-yellow-50 rounded-lg p-4 border-l-4 border-[#FBBC04]">
                <h3 className="text-sm font-medium text-gray-600 mb-3 uppercase flex items-center gap-2">
                  <Zap className="w-4 h-4 text-[#FBBC04]" />
                  Frontend Performance
                </h3>
                <div className="grid grid-cols-3 gap-3 mb-3">
                  <div className="text-center p-3 bg-white rounded border border-gray-200">
                    <p className="text-lg font-medium text-gray-900">{perfStats.requests}</p>
                    <p className="text-xs text-gray-500 mt-1">Requests</p>
                  </div>
                  <div className="text-center p-3 bg-white rounded border border-gray-200">
                    <p className="text-lg font-medium text-[#34A853]">{perfStats.cacheHits}</p>
                    <p className="text-xs text-gray-500 mt-1">Cache Hits</p>
                  </div>
                  <div className="text-center p-3 bg-white rounded border border-gray-200">
                    <p className="text-lg font-medium text-[#4285F4]">{perfStats.debounced}</p>
                    <p className="text-xs text-gray-500 mt-1">Debounced</p>
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm bg-white px-3 py-2 rounded border border-gray-200">
                    <span className="text-gray-600">Cached Queries</span>
                    <span className="font-medium text-gray-900">{cacheRef.current.size}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm bg-white px-3 py-2 rounded border border-gray-200">
                    <span className="text-gray-600">Saved Requests</span>
                    <span className="font-medium text-[#34A853]">{perfStats.cacheHits + perfStats.debounced}</span>
                  </div>
                  {perfStats.requests > 0 && (
                    <div className="flex items-center justify-between text-sm bg-white px-3 py-2 rounded border border-gray-200">
                      <span className="text-gray-600">Cache Hit Rate</span>
                      <span className="font-medium text-[#4285F4]">
                        {((perfStats.cacheHits / perfStats.requests) * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex justify-end">
              <button
                onClick={() => setShowStatsModal(false)}
                className="px-6 py-2 bg-[#4285F4] hover:bg-[#3367D6] text-white rounded text-sm font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Success Modal */}
      {showSuccessModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-sm w-full">
            <div className="p-6 text-center">
              <div className="bg-green-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 className="w-6 h-6 text-[#34A853]" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Success</h3>
              <p className="text-sm text-gray-600 mb-4">{successMessage}</p>
              <button
                onClick={() => setShowSuccessModal(false)}
                className="px-6 py-2 bg-[#4285F4] hover:bg-[#3367D6] text-white rounded text-sm font-medium transition-colors"
              >
                OK
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
