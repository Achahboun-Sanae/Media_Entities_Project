import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd
from typing import Dict, List, Tuple, Optional

load_dotenv()

class SupabaseManager:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "").strip()
        self.key = os.getenv("SUPABASE_KEY", "").strip()
        self.client = create_client(self.url, self.key)
        self._table_structure = self._detect_table_structure()

    def _detect_table_structure(self) -> Dict[str, Dict[str, List[str]]]:
        """Détecte automatiquement toutes les tables organisées par langue"""
        try:
            response = self.client.schema.tables()
            all_tables = [table['name'] for table in response] if response else []
        except:
            # Fallback si l'API schema n'est pas disponible
            all_tables = [
                'entite_fr_pers', 'entite_fr_loc', 'entite_fr_org', 'entite_fr_event',
                'entites_ar_pers', 'entites_ar_loc', 'entites_ar_org', 'entites_ar_event',
                'entite_en_pers', 'entite_en_loc', 'entite_en_org', 'entite_en_event',
                'relations_fr', 'relations_ar', 'relations_en'
            ]
        
        structure = {
            'fr': {'entities': [], 'relations': []},
            'en': {'entities': [], 'relations': []},
            'ar': {'entities': [], 'relations': []}
        }

        for table in all_tables:
            table_lower = table.lower()
            # Détection des tables françaises
            if any(prefix in table_lower for prefix in ['entite_fr_', 'entites_fr_']):
                structure['fr']['entities'].append(table)
            elif any(prefix in table_lower for prefix in ['relation_fr', 'relations_fr']):
                structure['fr']['relations'].append(table)
            # Détection des tables arabes
            elif any(prefix in table_lower for prefix in ['entite_ar_', 'entites_ar_']):
                structure['ar']['entities'].append(table)
            elif any(prefix in table_lower for prefix in ['relation_ar', 'relations_ar']):
                structure['ar']['relations'].append(table)
            # Détection des tables anglaises
            elif any(prefix in table_lower for prefix in ['entite_en_', 'entites_en_']):
                structure['en']['entities'].append(table)
            elif any(prefix in table_lower for prefix in ['relation_en', 'relations_en']):
                structure['en']['relations'].append(table)

        return structure

    def get_available_tables(self) -> List[str]:
        """Retourne toutes les tables disponibles (pour la compatibilité)"""
        tables = []
        for lang in self._table_structure.values():
            tables.extend(lang['entities'] + lang['relations'])
        return tables

    def load_data(self, lang: str) -> Dict:
        """Charge les données pour une langue spécifique"""
        entities = pd.DataFrame()
        for table in self._table_structure[lang]['entities']:
            df = self.get_table(table)  
            if not df.empty:
                entities = pd.concat([entities, df], ignore_index=True)
        
        relations = []
        for table in self._table_structure[lang]['relations']:
            df = self.get_table(table)  
            if not df.empty:
                source_col = next((c for c in df.columns if 'source' in c.lower()), None)
                target_col = next((c for c in df.columns if 'target' in c.lower()), None)
                type_col = next((c for c in df.columns if 'type' in c.lower() and 'entity' not in c.lower()), None)
                
                if all([source_col, target_col, type_col]):
                    relations.extend(df[[source_col, target_col, type_col]].to_records(index=False).tolist())
        
        return {
            'entities': entities,
            'relations': relations,
            'locations': entities[entities['type'].str.lower() == 'loc'] if 'type' in entities.columns else pd.DataFrame()
        }
    
    def get_table(self, table_name: str) -> pd.DataFrame:
        """Version optimisée avec gestion de la pagination"""
        try:
            all_data = []
            page_size = 1000  # Taille de page recommandée par Supabase
            page = 0
            
            while True:
                response = (self.client.table(table_name)
                            .select("*")
                            .range(page * page_size, (page + 1) * page_size - 1)
                            .execute())
                
                if not response.data:
                    break
                    
                all_data.extend(response.data)
                page += 1
                
                # Optionnel : affichage plus propre de la progression
                print(f"\rChargement : page {page} ({len(response.data)} enregistrements)", end="", flush=True)
                
            print()  # Nouvelle ligne après la progression
            return pd.DataFrame(all_data) if all_data else pd.DataFrame()
        
        except Exception as e:
            print(f"\nErreur lors du chargement: {str(e)}")
            return pd.DataFrame()

def get_supabase_manager():
    """Factory pour une instance unique"""
    global _manager
    if '_manager' not in globals():
        _manager = SupabaseManager()
    return _manager