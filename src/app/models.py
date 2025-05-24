from . import db
from datetime import datetime

class Cluster(db.Model):
    """Cluster model for storing cluster information"""
    __tablename__ = 'clusters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    color = db.Column(db.String(20), nullable=False)  # Hex color code
    avg_volatility = db.Column(db.Float, nullable=False)
    avg_change = db.Column(db.Float, nullable=False)
    avg_beta = db.Column(db.Float, nullable=False)
    risk_return_ratio = db.Column(db.Float, nullable=False)
    summary = db.Column(db.Text)
    investor_profile = db.Column(db.String(50))  # Conservative, Aggressive, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # İlişkiler
    stocks = db.relationship('Stock', backref='cluster', lazy=True)
    
    def __repr__(self):
        return f'<Cluster {self.id}: {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'avg_volatility': self.avg_volatility,
            'avg_change': self.avg_change,
            'avg_beta': self.avg_beta,
            'risk_return_ratio': self.risk_return_ratio,
            'summary': self.summary,
            'investor_profile': self.investor_profile,
            'stock_count': len(self.stocks)
        }

class Stock(db.Model):
    """Stock model for storing stock information"""
    __tablename__ = 'stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    
    # Fiyat geçmişi
    price_history = db.relationship('PriceHistory', backref='stock_ref', lazy=True, cascade='all, delete-orphan')
    
    # Basic statistics
    avg_price = db.Column(db.Float, nullable=False)
    volatility = db.Column(db.Float, nullable=False)
    avg_change = db.Column(db.Float, nullable=False)
    beta = db.Column(db.Float, nullable=False)
    risk_return_ratio = db.Column(db.Float, nullable=False)
    max_gain = db.Column(db.Float, nullable=False)
    max_loss = db.Column(db.Float, nullable=False)
    
    # Cluster relationship
    cluster_id = db.Column(db.Integer, db.ForeignKey('clusters.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Stock {self.code}>'

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'avg_price': self.avg_price,
            'volatility': self.volatility,
            'avg_change': self.avg_change,
            'beta': self.beta,
            'risk_return_ratio': self.risk_return_ratio,
            'max_gain': self.max_gain,
            'max_loss': self.max_loss,
            'cluster_id': self.cluster_id
        }

class PriceHistory(db.Model):
    """Price history model for storing daily stock prices"""
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    open_price = db.Column(db.Float, nullable=False)
    high_price = db.Column(db.Float, nullable=False)
    low_price = db.Column(db.Float, nullable=False)
    close_price = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint for stock and date combination
    __table_args__ = (db.UniqueConstraint('stock_id', 'date', name='_stock_date_uc'),)
    
    def __repr__(self):
        return f'<PriceHistory {self.stock_id} - {self.date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'stock_id': self.stock_id,
            'date': self.date.isoformat(),
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'close_price': self.close_price,
            'volume': self.volume,
            'created_at': self.created_at.isoformat()
        } 