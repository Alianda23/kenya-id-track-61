-- Add constituencies table to existing database
USE dig_id;

-- Create constituencies table
CREATE TABLE IF NOT EXISTS constituencies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add constituency field to officers table
ALTER TABLE officers ADD COLUMN IF NOT EXISTS constituency VARCHAR(100);

-- Insert some default constituencies (optional)
INSERT IGNORE INTO constituencies (name) VALUES 
('Nairobi West'),
('Nairobi East'), 
('Nairobi North'),
('Mombasa'),
('Kisumu'),
('Nakuru'),
('Eldoret'),
('Thika'),
('Kitale'),
('Garissa'),
('Machakos'),
('Nyeri');

-- Add 'suspended' status to officers
ALTER TABLE officers MODIFY COLUMN status ENUM('pending', 'approved', 'rejected', 'suspended') DEFAULT 'pending';

-- Add 'ready_for_dispatch' status to applications
ALTER TABLE applications MODIFY COLUMN status ENUM('submitted', 'approved', 'rejected', 'ready_for_dispatch', 'dispatched', 'ready_for_collection', 'collected') DEFAULT 'submitted';
