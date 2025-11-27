"""
IP Whitelist для проверки webhook запросов.
"""

from typing import List, Dict, Set
import ipaddress
import logging

logger = logging.getLogger(__name__)


class IPWhitelist:
    """
    Управление whitelist IP адресов для webhook запросов.
    
    Поддерживает как отдельные IP, так и CIDR диапазоны.
    """
    
    # Известные IP адреса платежных систем
    DEFAULT_WHITELISTS = {
        'yookassa': [
            '185.71.76.0/27',
            '185.71.77.0/27',
            '77.75.153.0/25',
            '77.75.156.11',
            '77.75.156.35',
            '77.75.154.128/25',
        ],
        'cryptopay': [
            # CryptoPay может использовать различные IP
            '0.0.0.0/0',  # Разрешить все (проверка только по подписи)
        ],
        'freekassa': [
            '168.119.157.136',
            '168.119.60.227',
            '138.201.88.124',
            '178.154.197.79',
        ],
        'tribute': [
            # Tribute IP адреса
            '0.0.0.0/0',  # Разрешить все (проверка только по подписи)
        ],
        'stars': [
            # Telegram IP адреса
            '149.154.160.0/20',
            '91.108.4.0/22',
        ],
        'panel': [
            # Локальные и доверенные IP
            '127.0.0.1',
            '::1',
        ],
    }
    
    def __init__(self, custom_whitelists: Dict[str, List[str]] = None):
        """
        Инициализация IP whitelist.
        
        Args:
            custom_whitelists: Пользовательские whitelist для провайдеров
                {
                    'provider_name': ['ip1', 'ip2', 'cidr_range'],
                    ...
                }
        """
        self.whitelists: Dict[str, Set[ipaddress.IPv4Network | ipaddress.IPv6Network]] = {}
        
        # Загружаем дефолтные whitelist
        for provider, ips in self.DEFAULT_WHITELISTS.items():
            self.whitelists[provider] = self._parse_ip_list(ips)
        
        # Добавляем пользовательские whitelist
        if custom_whitelists:
            for provider, ips in custom_whitelists.items():
                if provider in self.whitelists:
                    # Объединяем с существующими
                    self.whitelists[provider].update(self._parse_ip_list(ips))
                else:
                    # Создаем новый
                    self.whitelists[provider] = self._parse_ip_list(ips)
    
    def _parse_ip_list(
        self,
        ip_list: List[str]
    ) -> Set[ipaddress.IPv4Network | ipaddress.IPv6Network]:
        """
        Парсинг списка IP адресов и CIDR диапазонов.
        
        Args:
            ip_list: Список IP адресов и CIDR диапазонов
            
        Returns:
            Множество IP сетей
        """
        networks = set()
        
        for ip_str in ip_list:
            try:
                # Пытаемся распарсить как сеть
                network = ipaddress.ip_network(ip_str, strict=False)
                networks.add(network)
            except ValueError as e:
                logger.error(f"Invalid IP address or CIDR: {ip_str}, error: {e}")
        
        return networks
    
    def is_allowed(self, provider: str, ip_address: str) -> bool:
        """
        Проверить, разрешен ли IP адрес для провайдера.
        
        Args:
            provider: Название провайдера
            ip_address: IP адрес для проверки
            
        Returns:
            True если IP разрешен
        """
        if provider not in self.whitelists:
            logger.warning(f"No whitelist configured for provider: {provider}")
            return False
        
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Проверяем, входит ли IP в какую-либо разрешенную сеть
            for network in self.whitelists[provider]:
                if ip in network:
                    logger.debug(
                        f"IP {ip_address} allowed for {provider} "
                        f"(matches {network})"
                    )
                    return True
            
            logger.warning(
                f"IP {ip_address} not in whitelist for provider {provider}"
            )
            return False
            
        except ValueError as e:
            logger.error(f"Invalid IP address: {ip_address}, error: {e}")
            return False
    
    def add_ip(self, provider: str, ip_address: str) -> bool:
        """
        Добавить IP адрес в whitelist провайдера.
        
        Args:
            provider: Название провайдера
            ip_address: IP адрес или CIDR диапазон
            
        Returns:
            True если успешно добавлен
        """
        try:
            network = ipaddress.ip_network(ip_address, strict=False)
            
            if provider not in self.whitelists:
                self.whitelists[provider] = set()
            
            self.whitelists[provider].add(network)
            
            logger.info(
                f"Added {ip_address} to whitelist for provider {provider}"
            )
            return True
            
        except ValueError as e:
            logger.error(
                f"Failed to add IP {ip_address} for {provider}: {e}"
            )
            return False
    
    def remove_ip(self, provider: str, ip_address: str) -> bool:
        """
        Удалить IP адрес из whitelist провайдера.
        
        Args:
            provider: Название провайдера
            ip_address: IP адрес или CIDR диапазон
            
        Returns:
            True если успешно удален
        """
        if provider not in self.whitelists:
            logger.warning(f"No whitelist for provider: {provider}")
            return False
        
        try:
            network = ipaddress.ip_network(ip_address, strict=False)
            
            if network in self.whitelists[provider]:
                self.whitelists[provider].remove(network)
                logger.info(
                    f"Removed {ip_address} from whitelist for provider {provider}"
                )
                return True
            else:
                logger.warning(
                    f"IP {ip_address} not found in whitelist for {provider}"
                )
                return False
                
        except ValueError as e:
            logger.error(
                f"Failed to remove IP {ip_address} for {provider}: {e}"
            )
            return False
    
    def get_whitelist(self, provider: str) -> List[str]:
        """
        Получить whitelist для провайдера.
        
        Args:
            provider: Название провайдера
            
        Returns:
            Список IP адресов и CIDR диапазонов
        """
        if provider not in self.whitelists:
            return []
        
        return [str(network) for network in self.whitelists[provider]]
    
    def clear_whitelist(self, provider: str) -> bool:
        """
        Очистить whitelist для провайдера.
        
        Args:
            provider: Название провайдера
            
        Returns:
            True если успешно очищен
        """
        if provider in self.whitelists:
            self.whitelists[provider].clear()
            logger.info(f"Cleared whitelist for provider {provider}")
            return True
        
        return False
    
    def get_all_providers(self) -> List[str]:
        """
        Получить список всех провайдеров с whitelist.
        
        Returns:
            Список названий провайдеров
        """
        return list(self.whitelists.keys())
    
    def disable_whitelist(self, provider: str) -> bool:
        """
        Отключить проверку whitelist для провайдера (разрешить все IP).
        
        Args:
            provider: Название провайдера
            
        Returns:
            True если успешно отключен
        """
        try:
            # Добавляем 0.0.0.0/0 для разрешения всех IPv4
            self.whitelists[provider] = {
                ipaddress.ip_network('0.0.0.0/0'),
                ipaddress.ip_network('::/0'),  # IPv6
            }
            
            logger.warning(
                f"Whitelist disabled for provider {provider} - "
                f"all IPs are now allowed!"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable whitelist for {provider}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Dict[str, any]]:
        """
        Получить статистику по whitelist.
        
        Returns:
            Словарь со статистикой по каждому провайдеру
        """
        stats = {}
        
        for provider, networks in self.whitelists.items():
            stats[provider] = {
                'count': len(networks),
                'networks': [str(net) for net in networks],
                'allows_all': any(
                    net == ipaddress.ip_network('0.0.0.0/0') or
                    net == ipaddress.ip_network('::/0')
                    for net in networks
                )
            }
        
        return stats