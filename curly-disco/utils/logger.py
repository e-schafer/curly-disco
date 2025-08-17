"""
Configuration centralisée du logging pour le bot de trading
"""
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class TradingFormatter(logging.Formatter):
    """Formatter personnalisé avec couleurs et emojis pour le trading bot"""
    
    # Couleurs ANSI
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Vert
        'WARNING': '\033[33m',  # Jaune
        'ERROR': '\033[31m',    # Rouge
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    # Emojis par niveau
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '💥'
    }
    
    def format(self, record):
        # Ajouter emoji et couleur
        emoji = getattr(record, 'emoji', self.EMOJIS.get(record.levelname, 'ℹ️'))
        
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format de base avec couleur
        log_message = f"{color}[{record.levelname}]{reset} {emoji} {record.getMessage()}"
        
        # Ajouter contexte si disponible
        if hasattr(record, 'pair') and getattr(record, 'pair', None):
            log_message += f" | Pair: {getattr(record, 'pair')}"
        if hasattr(record, 'operation') and getattr(record, 'operation', None):
            log_message += f" | Op: {getattr(record, 'operation')}"
        if hasattr(record, 'amount') and getattr(record, 'amount', None):
            log_message += f" | Amount: {getattr(record, 'amount')}"
        
        # Timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        return f"{timestamp} | {log_message}"


class TradingLogger:
    """Gestionnaire de logging centralisé pour le bot de trading"""
    
    _instance: Optional['TradingLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self):
        """Configure le logger principal"""
        # Créer le répertoire de logs
        log_dir = Path(__file__).parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Logger principal
        self._logger = logging.getLogger('curly_disco')
        self._logger.setLevel(logging.DEBUG)
        
        # Éviter la duplication des handlers
        if self._logger.handlers:
            return
        
        # Handler console avec couleurs
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(TradingFormatter())
        
        # Handler fichier unique avec rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "trading.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)s | %(pathname)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        
        # Ajouter les handlers
        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)
        
        # Configurer tous les loggers pour utiliser le même fichier
        self._setup_specialized_loggers()
    
    def _setup_specialized_loggers(self):
        """Configure tous les loggers pour utiliser le même fichier"""
        # Configurer les loggers spécialisés pour utiliser le logger parent
        specialized_loggers = ['orders', 'trades', 'strategy', 'websocket', 'api']
        
        for logger_name in specialized_loggers:
            logger = logging.getLogger(f'curly_disco.{logger_name}')
            logger.setLevel(logging.DEBUG)
            # Ne pas ajouter de handlers séparés - utiliser ceux du parent
            logger.propagate = True  # S'assurer que les logs remontent au parent
    
    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            raise RuntimeError("Logger not initialized. Call setup() first.")
        return self._logger

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Obtient un logger spécialisé"""
        if name:
            return logging.getLogger(f"curly_disco.{name}")
        if self._logger is None:
            raise RuntimeError("Logger not initialized. Call setup() first.")
        return self._logger
# Instance globale
trading_logger = TradingLogger()

# Fonctions utilitaires pour le logging contextuel
def log_order(level: str, message: str, pair: Optional[str] = None, amount: Optional[float] = None, **kwargs):
    """Log spécialisé pour les ordres"""
    logger = trading_logger.get_logger('orders')
    extra = {'emoji': '💰', 'pair': pair, 'amount': amount, **kwargs}
    getattr(logger, level.lower())(message, extra=extra)

def log_trade(level: str, message: str, pair: Optional[str] = None, pnl: Optional[float] = None, **kwargs):
    """Log spécialisé pour les trades"""
    logger = trading_logger.get_logger('trades')
    extra = {'emoji': '📈' if pnl and pnl > 0 else '📉', 'pair': pair, 'pnl': pnl, **kwargs}
    getattr(logger, level.lower())(message, extra=extra)

def log_strategy(level: str, message: str, **kwargs):
    """Log spécialisé pour les stratégies"""
    logger = trading_logger.get_logger('strategy')
    extra = {'emoji': '🎯', **kwargs}
    getattr(logger, level.lower())(message, extra=extra)

def log_websocket(level: str, message: str, **kwargs):
    """Log spécialisé pour WebSocket"""
    logger = trading_logger.get_logger('websocket')
    extra = {'emoji': '🔗', **kwargs}
    getattr(logger, level.lower())(message, extra=extra)

def log_api(level: str, message: str, endpoint: Optional[str] = None, **kwargs):
    """Log spécialisé pour les appels API"""
    logger = trading_logger.get_logger('api')
    extra = {'emoji': '🌐', 'endpoint': endpoint, **kwargs}
    getattr(logger, level.lower())(message, extra=extra)
