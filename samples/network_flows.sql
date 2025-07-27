CREATE RANDOM STREAM network_flows
(
  `timestamp` datetime64(3) DEFAULT now64(),
  `flow_id` string DEFAULT concat('flow_', uuid()),
  
  -- Network endpoints with realistic IP distributions
  `source_ip` string DEFAULT multi_if(
    (rand() % 100) <= 60, concat('10.', to_string(rand(1) % 256), '.', to_string(rand(2) % 256), '.', to_string(rand(3) % 256)), -- 60% internal 10.x.x.x
    (rand() % 100) <= 80, concat('192.168.', to_string(rand(4) % 256), '.', to_string(rand(5) % 256)), -- 20% internal 192.168.x.x
    concat(to_string(rand(6) % 223 + 1), '.', to_string(rand(7) % 256), '.', to_string(rand(8) % 256), '.', to_string(rand(9) % 256)) -- 20% external
  ),
  `dest_ip` string DEFAULT multi_if(
    (rand(10) % 100) <= 40, concat('10.', to_string(rand(11) % 256), '.', to_string(rand(12) % 256), '.', to_string(rand(13) % 256)), -- 40% internal
    (rand(10) % 100) <= 60, concat('192.168.', to_string(rand(14) % 256), '.', to_string(rand(15) % 256)), -- 20% internal
    concat(to_string(rand(16) % 223 + 1), '.', to_string(rand(17) % 256), '.', to_string(rand(18) % 256), '.', to_string(rand(19) % 256)) -- 40% external
  ),
  
  -- Port information with realistic distributions
  `source_port` uint16 DEFAULT multi_if(
    (rand(20) % 100) <= 70, 32768 + (rand(21) % 28232), -- 70% ephemeral ports (32768-65535)
    (rand(20) % 100) <= 85, 1024 + (rand(22) % 31744),  -- 15% registered ports (1024-32767)
    rand(23) % 1024                                      -- 15% well-known ports (0-1023)
  ),
  `dest_port` uint16 DEFAULT multi_if(
    (rand(24) % 100) <= 50, array_element([80, 443, 53, 25, 993, 995], (rand(25) % 6) + 1), -- 50% common services
    (rand(24) % 100) <= 70, array_element([22, 21, 23, 3389, 5432, 3306, 1433], (rand(26) % 7) + 1), -- 20% admin services
    (rand(24) % 100) <= 85, 1024 + (rand(27) % 31744),  -- 15% registered ports
    32768 + (rand(28) % 28232)                           -- 15% ephemeral ports
  ),
  
  -- Protocol information
  `protocol` enum8('TCP' = 6, 'UDP' = 17, 'ICMP' = 1, 'OTHER' = 127) DEFAULT multi_if(
    (rand(29) % 100) <= 80, 6,  -- 80% TCP
    (rand(29) % 100) <= 95, 17, -- 15% UDP
    (rand(29) % 100) <= 98, 1,  -- 3% ICMP
    254                          -- 2% Other
  ),
  
  -- Flow characteristics with realistic patterns
  `bytes_sent` uint64 DEFAULT multi_if(
    dest_port = 80 OR dest_port = 443, round(rand_log_normal(10, 2)), -- HTTP/HTTPS: larger transfers
    dest_port = 53, round(rand_exponential(0.01)),                    -- DNS: small queries
    dest_port = 25, round(rand_log_normal(8, 1.5)),                   -- SMTP: medium emails
    round(rand_log_normal(6, 2))                                      -- Default: varied sizes
  ),
  `bytes_received` uint64 DEFAULT multi_if(
    dest_port = 80 OR dest_port = 443, bytes_sent * rand_uniform(0.1, 10), -- HTTP responses vary
    dest_port = 53, round(rand_exponential(0.005)),                         -- DNS responses small
    dest_port = 25, round(rand_uniform(100, 1000)),                         -- SMTP confirmations
    bytes_sent * rand_uniform(0.1, 5)                                       -- Default ratio
  ),
  `packets_sent` uint32 DEFAULT round(bytes_sent / rand_uniform(64, 1500)), -- MTU consideration
  `packets_received` uint32 DEFAULT round(bytes_received / rand_uniform(64, 1500)),
  
  -- Timing information
  `flow_duration_ms` uint32 DEFAULT multi_if(
    dest_port = 53, round(rand_exponential(0.01)),      -- DNS: very quick
    dest_port = 80 OR dest_port = 443, round(rand_log_normal(8, 1)), -- HTTP: varies widely
    protocol = 17, round(rand_exponential(0.001)),      -- UDP: often short
    round(rand_log_normal(6, 2))                        -- TCP: moderate duration
  ),
  `tcp_flags` string DEFAULT multi_if(
    protocol = 6 AND flow_duration_ms > 1000, 'SYN,ACK,PSH,FIN', -- Normal TCP flow
    protocol = 6 AND flow_duration_ms <= 1000, 'SYN,RST',       -- Quick reset
    protocol = 6, 'SYN,ACK,FIN',                                 -- Basic TCP
    ''                                                            -- Non-TCP
  )
)
SETTINGS eps = 10; -- High volume network monitoring