CREATE RANDOM STREAM financial_trading
(
  `timestamp` datetime64(3) DEFAULT now64(),
  `trade_id` string DEFAULT concat('trade_', uuid()),
  
  -- Financial instruments with realistic symbols
  `symbol` string DEFAULT array_element([
    'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX',
    'BTC-USD', 'ETH-USD', 'SPY', 'QQQ', 'GLD', 'EURUSD', 'GBPUSD'
  ], (rand() % 15) + 1),
  
  -- Price movements with student-t distribution (fat tails)
  `price` float64 DEFAULT greatest(0.01, 
    100 * exp(rand_student_t(3) * 0.02)  -- Realistic price volatility
  ),
  `price_change` float64 DEFAULT rand_student_t(3) * 0.5, -- Fat-tailed returns
  `price_change_percent` float64 DEFAULT price_change / price * 100,
  
  -- Volume with exponential distribution
  `volume` uint64 DEFAULT round(rand_exponential(0.00001)), -- High volume distribution
  `volume_weighted_price` float64 DEFAULT price * (1 + rand_normal(0, 0.001)),
  
  -- Bid-Ask spread with exponential distribution
  `bid_price` float64 DEFAULT price * (1 - rand_exponential(100) / 10000),
  `ask_price` float64 DEFAULT price * (1 + rand_exponential(100) / 10000),
  `spread_bps` float64 DEFAULT (ask_price - bid_price) / price * 10000,
  
  -- Market depth (order book) - simplified for Timeplus
  `total_bid_size` uint32 DEFAULT round(rand_exponential(0.001)),
  `total_ask_size` uint32 DEFAULT round(rand_exponential(0.001)),
  
  -- Trading venue and liquidity
  `exchange` enum8(
    'NYSE' = 1, 'NASDAQ' = 2, 'BATS' = 3, 'EDGX' = 4, 'IEX' = 5, 'CBOE' = 6, 'ARCA' = 7
  ) DEFAULT (rand(1) % 7) + 1,
  `market_maker` string DEFAULT concat('MM_', to_string(rand(2) % 20)),
  
  -- Order characteristics
  `order_type` enum8(
    'market' = 1, 'limit' = 2, 'stop' = 3, 'stop_limit' = 4, 'iceberg' = 5
  ) DEFAULT (rand(3) % 5) + 1,
  `order_side` enum8('buy' = 1, 'sell' = 2) DEFAULT (rand(4) % 2) + 1,
  `order_size` float64 DEFAULT round(rand_log_normal(6, 2)), -- Log-normal order sizes
  
  -- Algorithmic trading indicators
  `algo_type` enum8(
    'momentum' = 1, 'mean_reversion' = 2, 'arbitrage' = 3, 'market_making' = 4, 'trend_following' = 5
  ) DEFAULT (rand(5) % 5) + 1,
  `execution_strategy` enum8(
    'TWAP' = 1, 'VWAP' = 2, 'POV' = 3, 'implementation_shortfall' = 4, 'aggressive' = 5
  ) DEFAULT (rand(6) % 5) + 1,
  
  -- Risk metrics
  `var_95` float64 DEFAULT abs(rand_normal(0, price * 0.05)), -- Value at Risk
  `volatility_annualized` float64 DEFAULT rand_log_normal(-2.0, 0.5), -- 0.1-1.0 range
  `beta` float64 DEFAULT rand_normal(1.0, 0.3), -- Market beta

  -- Market microstructure
  `tick_direction` int8 DEFAULT CASE (rand(11) % 3)
    WHEN 0 THEN 1   -- Uptick
    WHEN 1 THEN -1  -- Downtick  
    ELSE 0          -- No change
  END,
  `trade_condition` enum8(
    'regular' = 1, 'opening' = 2, 'closing' = 3, 'cross' = 4, 'late' = 5, 'cancelled' = 6
  ) DEFAULT (rand(12) % 6) + 1,
  
  -- Performance metrics
  `latency_microseconds` uint32 DEFAULT round(rand_exponential(0.001)), -- Low latency
  `slippage_bps` float64 DEFAULT abs(rand_normal(0, 2)), -- Execution slippage
  
  -- Market sentiment indicators
  `sentiment_score` float32 DEFAULT rand_normal(0, 1), -- -3 to +3 sentiment
  `news_impact_score` float32 DEFAULT rand_exponential(1), -- News impact
  `social_media_mentions` uint32 DEFAULT rand_poisson(50),
  
  -- Trading session information
  `is_market_hours` bool DEFAULT to_hour(timestamp) BETWEEN 9 AND 16,
  `trading_session` enum8('pre_market' = 1, 'regular' = 2, 'after_hours' = 3) DEFAULT multi_if(
    to_hour(timestamp) < 9, 1,
    to_hour(timestamp) >= 9 AND to_hour(timestamp) <= 16, 2,
    3
  ),
  
  -- Additional metadata
  `trade_metadata` string DEFAULT concat('{"symbol":"', symbol, '","volume":', to_string(volume), '}'),
  `risk_flags` array(string) DEFAULT multi_if(
    volatility_annualized > 0.5, ['high_volatility'],
    volume > 1000000, ['high_volume'],
    []
  )
)
SETTINGS eps = 10;