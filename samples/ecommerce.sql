CREATE RANDOM STREAM ecommerce_events
(
  -- Temporal data with realistic patterns
  `timestamp` datetime64(3) DEFAULT now64() - (rand_poisson(60) * 1000), -- Events with randaom latency up to 1 minute
  `event_id` string DEFAULT concat('evt_', uuid()),
  
  -- Customer demographics with weighted distribution
  `customer_id` uint32 DEFAULT multi_if(
    (rand() % 100) <= 60, rand() % 50000,        -- 60% regular customers  
    (rand() % 100) <= 80, 50000 + (rand(1) % 10000),  -- 20% premium customers
    60000 + (rand(2) % 5000)                     -- 20% VIP customers
  ),
  
  -- Realistic email patterns
  `customer_email` string DEFAULT concat(
    array_element(['john', 'jane', 'mike', 'sarah', 'david', 'lisa'], (rand(3) % 6) + 1),
    '.', 
    array_element(['smith', 'jones', 'brown', 'davis', 'wilson'], (rand(4) % 5) + 1),
    to_string(rand_uniform(1980, 2005)),
    '@',
    array_element(['gmail.com', 'yahoo.com', 'hotmail.com', 'company.com'], (rand(5) % 4) + 1)
  ),
  
  -- Geographic distribution with realistic coordinates
  `customer_lat` float64 DEFAULT multi_if(
    (rand(6) % 5) = 0, round(rand_uniform(40.0, 45.0), 6),   -- Northeast US
    (rand(6) % 5) = 1, round(rand_uniform(32.0, 37.0), 6),   -- Southeast US  
    (rand(6) % 5) = 2, round(rand_uniform(41.0, 48.0), 6),   -- Midwest US
    (rand(6) % 5) = 3, round(rand_uniform(25.0, 35.0), 6),   -- Southwest US
    round(rand_uniform(45.0, 49.0), 6)                       -- Northwest US
  ),
  `customer_lon` float64 DEFAULT multi_if(
    (rand(7) % 5) = 0, round(rand_uniform(-80.0, -70.0), 6),  -- Northeast
    (rand(7) % 5) = 1, round(rand_uniform(-90.0, -75.0), 6),  -- Southeast
    (rand(7) % 5) = 2, round(rand_uniform(-95.0, -80.0), 6),  -- Midwest  
    (rand(7) % 5) = 3, round(rand_uniform(-120.0, -100.0), 6), -- Southwest
    round(rand_uniform(-125.0, -115.0), 6)                   -- Northwest
  ),
  
  -- Event types with realistic probability distribution
  `event_type` string DEFAULT array_element([
    'product_view', 'add_to_cart', 'remove_from_cart', 'checkout_start', 
    'payment_complete', 'account_created', 'login', 'logout', 'search'
  ], (rand(8) % 9) + 1),
  
  -- Product data with categories and realistic pricing
  `product_id` string DEFAULT concat('prod_', to_string(rand(9) % 10000)),
  `product_category` string DEFAULT array_element([
    'Electronics', 'Clothing', 'Books', 'Home & Garden', 'Sports',
    'Beauty', 'Automotive', 'Toys', 'Health', 'Food'
  ], (rand(10) % 10) + 1),
  
  -- Log-normal distribution for realistic pricing
  `product_price` float64 DEFAULT round(exp(rand_normal(3.5, 1.2)), 2), -- $5 to $500+ range
  
  -- Session data with exponential decay
  `session_id` string DEFAULT concat('sess_', random_printable_ascii(12)),
  `session_duration_seconds` uint32 DEFAULT round(rand_exponential(0.001)), -- Long tail
  
  -- Device and browser info
  `user_agent` string DEFAULT array_element([
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/14.1',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1) Mobile Safari/604.1',
    'Mozilla/5.0 (Android 11; Mobile) Chrome/91.0'
  ], (rand(11) % 4) + 1),
  
  -- Marketing attribution with UTM parameters
  `utm_source` string DEFAULT array_element([
    'google', 'facebook', 'email', 'direct', 'instagram', 'twitter'
  ], (rand(12) % 6) + 1),
  `utm_campaign` string DEFAULT concat(
    array_element(['summer', 'winter', 'black_friday', 'new_year'], (rand(13) % 4) + 1),
    '_', to_string(2024 + (rand(14) % 2))
  ),
  
  -- Revenue with conditional logic
  `revenue` float64 DEFAULT multi_if(
    event_type = 'payment_complete', product_price,
    event_type = 'add_to_cart', 0,
    0
  ),
  
  -- Additional fields using supported Timeplus types
  `is_premium_customer` bool DEFAULT customer_id > 50000,
  `customer_age_group` enum8('18-25' = 1, '26-35' = 2, '36-45' = 3, '46-55' = 4, '56+' = 5) 
    DEFAULT (rand(15) % 5) + 1,
  `tags` array(string) DEFAULT array_slice(['new_customer', 'returning', 'vip', 'mobile_user', 'email_subscriber'], 1, (rand(16) % 3) + 1),
  `metadata` string DEFAULT concat('{"device_type":"', 
    array_element(['mobile', 'desktop', 'tablet'], (rand(17) % 3) + 1), 
    '","browser":"', 
    array_element(['chrome', 'safari', 'firefox'], (rand(18) % 3) + 1), '"}')
)
SETTINGS eps = 50;