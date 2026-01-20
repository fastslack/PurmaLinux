"""
PurmaLinux - Model Manager
===========================
Author: Matías Aguirre
Company: Matware

Gestión sencilla de modelos AI locales con Ollama.
Descarga, administra y usa modelos libres fácilmente.
"""

import asyncio
import json
import httpx
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("purma.models")

# ============================================
# Model Catalog - Modelos Recomendados
# ============================================

RECOMMENDED_MODELS = {
    # General Purpose
    "llama3.2": {
        "name": "LLaMA 3.2",
        "description": "Meta's latest model. Great all-rounder for chat and reasoning.",
        "size": "2GB",
        "parameters": "3B",
        "category": "general",
        "tags": ["chat", "reasoning", "coding"],
        "recommended": True,
        "vram": "4GB"
    },
    "llama3.2:1b": {
        "name": "LLaMA 3.2 1B",
        "description": "Lightweight version, fast and efficient.",
        "size": "1.3GB",
        "parameters": "1B",
        "category": "general",
        "tags": ["chat", "fast", "low-resource"],
        "recommended": True,
        "vram": "2GB"
    },
    "mistral": {
        "name": "Mistral 7B",
        "description": "Excellent performance-to-size ratio. Great for most tasks.",
        "size": "4.1GB",
        "parameters": "7B",
        "category": "general",
        "tags": ["chat", "reasoning", "efficient"],
        "recommended": True,
        "vram": "8GB"
    },
    "mixtral": {
        "name": "Mixtral 8x7B",
        "description": "Mixture of experts. Powerful but requires more resources.",
        "size": "26GB",
        "parameters": "47B (8x7B MoE)",
        "category": "general",
        "tags": ["powerful", "reasoning", "coding"],
        "recommended": False,
        "vram": "32GB"
    },
    "gemma2": {
        "name": "Gemma 2",
        "description": "Google's efficient open model. Good for chat.",
        "size": "5.4GB",
        "parameters": "9B",
        "category": "general",
        "tags": ["chat", "google", "efficient"],
        "recommended": True,
        "vram": "8GB"
    },
    "gemma2:2b": {
        "name": "Gemma 2 2B",
        "description": "Tiny but capable. Perfect for low-resource systems.",
        "size": "1.6GB",
        "parameters": "2B",
        "category": "general",
        "tags": ["fast", "tiny", "efficient"],
        "recommended": True,
        "vram": "3GB"
    },
    "phi3": {
        "name": "Phi-3",
        "description": "Microsoft's compact powerhouse. Excellent reasoning.",
        "size": "2.2GB",
        "parameters": "3.8B",
        "category": "general",
        "tags": ["reasoning", "microsoft", "compact"],
        "recommended": True,
        "vram": "4GB"
    },
    "qwen2.5": {
        "name": "Qwen 2.5",
        "description": "Alibaba's latest. Strong multilingual support.",
        "size": "4.4GB",
        "parameters": "7B",
        "category": "general",
        "tags": ["multilingual", "chat", "chinese"],
        "recommended": True,
        "vram": "8GB"
    },

    # Coding Models
    "codellama": {
        "name": "Code Llama",
        "description": "Specialized for code generation and understanding.",
        "size": "3.8GB",
        "parameters": "7B",
        "category": "coding",
        "tags": ["code", "programming", "completion"],
        "recommended": True,
        "vram": "8GB"
    },
    "codellama:13b": {
        "name": "Code Llama 13B",
        "description": "Larger coding model for complex tasks.",
        "size": "7.4GB",
        "parameters": "13B",
        "category": "coding",
        "tags": ["code", "programming", "powerful"],
        "recommended": False,
        "vram": "16GB"
    },
    "codegemma": {
        "name": "CodeGemma",
        "description": "Google's coding specialist. Fast completions.",
        "size": "5GB",
        "parameters": "7B",
        "category": "coding",
        "tags": ["code", "google", "completion"],
        "recommended": True,
        "vram": "8GB"
    },
    "deepseek-coder-v2": {
        "name": "DeepSeek Coder V2",
        "description": "Excellent for code with 128K context window.",
        "size": "8.9GB",
        "parameters": "16B",
        "category": "coding",
        "tags": ["code", "long-context", "powerful"],
        "recommended": True,
        "vram": "16GB"
    },
    "starcoder2": {
        "name": "StarCoder2",
        "description": "BigCode's coding model. Good for completions.",
        "size": "4GB",
        "parameters": "7B",
        "category": "coding",
        "tags": ["code", "completion", "bigcode"],
        "recommended": False,
        "vram": "8GB"
    },

    # Vision Models
    "llava": {
        "name": "LLaVA",
        "description": "Vision + Language. Can analyze images.",
        "size": "4.7GB",
        "parameters": "7B",
        "category": "vision",
        "tags": ["vision", "multimodal", "images"],
        "recommended": True,
        "vram": "8GB"
    },
    "llava-llama3": {
        "name": "LLaVA LLaMA3",
        "description": "Latest LLaVA with LLaMA3 base. Better vision.",
        "size": "5.5GB",
        "parameters": "8B",
        "category": "vision",
        "tags": ["vision", "multimodal", "latest"],
        "recommended": True,
        "vram": "10GB"
    },
    "moondream": {
        "name": "Moondream",
        "description": "Tiny vision model. Fast image analysis.",
        "size": "1.7GB",
        "parameters": "1.8B",
        "category": "vision",
        "tags": ["vision", "tiny", "fast"],
        "recommended": True,
        "vram": "3GB"
    },

    # Embedding Models
    "nomic-embed-text": {
        "name": "Nomic Embed",
        "description": "Text embeddings for RAG and search.",
        "size": "274MB",
        "parameters": "137M",
        "category": "embedding",
        "tags": ["embeddings", "rag", "search"],
        "recommended": True,
        "vram": "1GB"
    },
    "mxbai-embed-large": {
        "name": "MixedBread Embed Large",
        "description": "High quality embeddings. Better accuracy.",
        "size": "670MB",
        "parameters": "335M",
        "category": "embedding",
        "tags": ["embeddings", "rag", "quality"],
        "recommended": True,
        "vram": "2GB"
    },

    # Specialized
    "neural-chat": {
        "name": "Neural Chat",
        "description": "Intel's chat model. Optimized for CPUs.",
        "size": "4.1GB",
        "parameters": "7B",
        "category": "chat",
        "tags": ["chat", "intel", "cpu-optimized"],
        "recommended": False,
        "vram": "8GB"
    },
    "dolphin-mixtral": {
        "name": "Dolphin Mixtral",
        "description": "Uncensored Mixtral. No content filters.",
        "size": "26GB",
        "parameters": "47B",
        "category": "uncensored",
        "tags": ["uncensored", "powerful", "unrestricted"],
        "recommended": False,
        "vram": "32GB"
    },
    "tinyllama": {
        "name": "TinyLlama",
        "description": "Extremely small. For edge devices.",
        "size": "638MB",
        "parameters": "1.1B",
        "category": "tiny",
        "tags": ["tiny", "edge", "fast"],
        "recommended": False,
        "vram": "2GB"
    },
}

# Starter Packs - Conjuntos recomendados
STARTER_PACKS = {
    "minimal": {
        "name": "Minimal",
        "description": "Basic setup for low-resource systems (4GB RAM)",
        "models": ["llama3.2:1b", "nomic-embed-text"],
        "total_size": "~1.6GB"
    },
    "standard": {
        "name": "Standard",
        "description": "Recommended setup for most users (8GB RAM)",
        "models": ["llama3.2", "codellama", "nomic-embed-text"],
        "total_size": "~6GB"
    },
    "developer": {
        "name": "Developer",
        "description": "Full coding setup (16GB RAM)",
        "models": ["llama3.2", "deepseek-coder-v2", "codegemma", "mxbai-embed-large"],
        "total_size": "~19GB"
    },
    "creative": {
        "name": "Creative",
        "description": "For image analysis and content (16GB RAM)",
        "models": ["mistral", "llava-llama3", "moondream"],
        "total_size": "~12GB"
    },
    "poweruser": {
        "name": "Power User",
        "description": "Everything you need (32GB+ RAM)",
        "models": ["mixtral", "deepseek-coder-v2", "llava-llama3", "mxbai-embed-large"],
        "total_size": "~42GB"
    }
}


# ============================================
# Ollama Client
# ============================================

class OllamaClient:
    """Cliente para interactuar con Ollama"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout for downloads

    async def is_running(self) -> bool:
        """Verifica si Ollama está corriendo"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[Dict]:
        """Lista modelos instalados"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
            return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    async def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Obtiene información detallada de un modelo"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/show",
                json={"name": model_name}
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return None

    async def pull_model(self, model_name: str, progress_callback=None) -> bool:
        """Descarga un modelo con progreso"""
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=None  # No timeout for downloads
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if progress_callback:
                            await progress_callback(data)
                        if data.get("status") == "success":
                            return True
            return True
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False

    async def delete_model(self, model_name: str) -> bool:
        """Elimina un modelo"""
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/delete",
                json={"name": model_name}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            return False

    async def copy_model(self, source: str, destination: str) -> bool:
        """Copia/renombra un modelo"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/copy",
                json={"source": source, "destination": destination}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error copying model: {e}")
            return False

    async def close(self):
        """Cierra el cliente"""
        await self.client.aclose()


# ============================================
# Model Manager
# ============================================

class PurmaModelManager:
    """Gestor de modelos AI para PurmaLinux"""

    def __init__(self):
        self.client = OllamaClient()
        self.catalog = RECOMMENDED_MODELS
        self.packs = STARTER_PACKS

    async def check_ollama(self) -> Dict:
        """Verifica estado de Ollama"""
        running = await self.client.is_running()
        return {
            "running": running,
            "message": "Ollama is running" if running else "Ollama is not running. Start with: ollama serve"
        }

    async def get_installed_models(self) -> List[Dict]:
        """Obtiene modelos instalados con info adicional"""
        models = await self.client.list_models()
        result = []

        for model in models:
            name = model.get("name", "").split(":")[0]
            info = self.catalog.get(name, {})

            result.append({
                "name": model.get("name"),
                "size": model.get("size", 0),
                "size_human": self._format_size(model.get("size", 0)),
                "modified": model.get("modified_at"),
                "category": info.get("category", "custom"),
                "description": info.get("description", "Custom or unknown model"),
                "tags": info.get("tags", [])
            })

        return result

    async def get_available_models(self, category: str = None) -> List[Dict]:
        """Obtiene modelos disponibles para descargar"""
        installed = await self.get_installed_models()
        installed_names = {m["name"].split(":")[0] for m in installed}

        result = []
        for model_id, info in self.catalog.items():
            if category and info.get("category") != category:
                continue

            base_name = model_id.split(":")[0]
            is_installed = base_name in installed_names or model_id in [m["name"] for m in installed]

            result.append({
                "id": model_id,
                "installed": is_installed,
                **info
            })

        return result

    async def get_recommended(self) -> List[Dict]:
        """Obtiene modelos recomendados"""
        models = await self.get_available_models()
        return [m for m in models if m.get("recommended", False)]

    async def search_models(self, query: str) -> List[Dict]:
        """Busca modelos por nombre o tags"""
        query = query.lower()
        models = await self.get_available_models()

        results = []
        for model in models:
            # Search in name, description, and tags
            if (query in model["id"].lower() or
                query in model.get("description", "").lower() or
                any(query in tag for tag in model.get("tags", []))):
                results.append(model)

        return results

    async def install_model(self, model_id: str, progress_callback=None) -> Dict:
        """Instala un modelo"""
        # Check if it's a known model
        if model_id not in self.catalog:
            logger.warning(f"Model {model_id} not in catalog, attempting anyway...")

        async def internal_progress(data):
            status = data.get("status", "")
            if "pulling" in status:
                completed = data.get("completed", 0)
                total = data.get("total", 0)
                if total > 0:
                    percent = (completed / total) * 100
                    if progress_callback:
                        await progress_callback({
                            "status": "downloading",
                            "percent": percent,
                            "completed": self._format_size(completed),
                            "total": self._format_size(total)
                        })
            elif progress_callback:
                await progress_callback({"status": status})

        success = await self.client.pull_model(model_id, internal_progress)

        return {
            "success": success,
            "model": model_id,
            "message": f"Model {model_id} installed successfully" if success else f"Failed to install {model_id}"
        }

    async def uninstall_model(self, model_id: str) -> Dict:
        """Desinstala un modelo"""
        success = await self.client.delete_model(model_id)
        return {
            "success": success,
            "model": model_id,
            "message": f"Model {model_id} removed" if success else f"Failed to remove {model_id}"
        }

    async def install_pack(self, pack_id: str, progress_callback=None) -> Dict:
        """Instala un pack de modelos"""
        if pack_id not in self.packs:
            return {"success": False, "message": f"Pack '{pack_id}' not found"}

        pack = self.packs[pack_id]
        results = []

        for i, model in enumerate(pack["models"]):
            if progress_callback:
                await progress_callback({
                    "status": "installing_pack",
                    "current": i + 1,
                    "total": len(pack["models"]),
                    "model": model
                })

            result = await self.install_model(model, progress_callback)
            results.append(result)

        success = all(r["success"] for r in results)
        return {
            "success": success,
            "pack": pack_id,
            "models": results,
            "message": f"Pack '{pack['name']}' installed" if success else "Some models failed to install"
        }

    def get_packs(self) -> Dict:
        """Obtiene starter packs disponibles"""
        return self.packs

    def get_categories(self) -> List[str]:
        """Obtiene categorías de modelos"""
        categories = set()
        for info in self.catalog.values():
            categories.add(info.get("category", "general"))
        return sorted(list(categories))

    def get_model_card(self, model_id: str) -> Optional[Dict]:
        """Obtiene la card de un modelo del catálogo"""
        return self.catalog.get(model_id)

    async def get_system_info(self) -> Dict:
        """Obtiene información del sistema para recomendar modelos"""
        import psutil

        memory = psutil.virtual_memory()
        ram_gb = memory.total / (1024 ** 3)

        # Detectar GPU (simplificado)
        gpu_info = "Unknown"
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                gpu_info = result.stdout.strip()
        except Exception:
            pass

        # Recomendar pack basado en RAM
        if ram_gb >= 32:
            recommended_pack = "poweruser"
        elif ram_gb >= 16:
            recommended_pack = "developer"
        elif ram_gb >= 8:
            recommended_pack = "standard"
        else:
            recommended_pack = "minimal"

        return {
            "ram_total_gb": round(ram_gb, 1),
            "ram_available_gb": round(memory.available / (1024 ** 3), 1),
            "gpu": gpu_info,
            "recommended_pack": recommended_pack,
            "pack_info": self.packs[recommended_pack]
        }

    def _format_size(self, size_bytes: int) -> str:
        """Formatea tamaño en bytes a human readable"""
        if size_bytes == 0:
            return "0B"
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024
            i += 1
        return f"{size_bytes:.1f}{units[i]}"

    async def close(self):
        """Cierra el cliente"""
        await self.client.close()


# ============================================
# Singleton
# ============================================

_model_manager: Optional[PurmaModelManager] = None

def get_model_manager() -> PurmaModelManager:
    """Obtiene el model manager singleton"""
    global _model_manager
    if _model_manager is None:
        _model_manager = PurmaModelManager()
    return _model_manager


# ============================================
# CLI Functions
# ============================================

async def cli_list_models():
    """CLI: Lista modelos instalados"""
    manager = get_model_manager()

    # Check Ollama
    status = await manager.check_ollama()
    if not status["running"]:
        print(f"❌ {status['message']}")
        return

    models = await manager.get_installed_models()

    if not models:
        print("📦 No models installed yet.")
        print("   Run: purma models install llama3.2")
        return

    print("\n📦 Installed Models:\n")
    print(f"{'MODEL':<30} {'SIZE':<10} {'CATEGORY':<12}")
    print("─" * 55)

    for model in models:
        print(f"{model['name']:<30} {model['size_human']:<10} {model['category']:<12}")

    print(f"\n   Total: {len(models)} model(s)\n")


async def cli_available_models(category: str = None):
    """CLI: Lista modelos disponibles"""
    manager = get_model_manager()

    models = await manager.get_available_models(category)

    print(f"\n🌐 Available Models{f' ({category})' if category else ''}:\n")
    print(f"{'MODEL':<25} {'SIZE':<8} {'PARAMS':<10} {'STATUS':<12} {'DESCRIPTION'}")
    print("─" * 100)

    for model in models:
        status = "✓ Installed" if model["installed"] else ""
        rec = "⭐" if model.get("recommended") else "  "
        print(f"{rec}{model['id']:<23} {model['size']:<8} {model['parameters']:<10} {status:<12} {model['description'][:40]}")

    print(f"\n   ⭐ = Recommended\n")


async def cli_install_model(model_id: str):
    """CLI: Instala un modelo"""
    manager = get_model_manager()

    status = await manager.check_ollama()
    if not status["running"]:
        print(f"❌ {status['message']}")
        return

    print(f"\n📥 Installing {model_id}...\n")

    async def progress(data):
        if data.get("percent"):
            print(f"\r   Downloading: {data['percent']:.1f}% ({data['completed']}/{data['total']})", end="", flush=True)
        elif data.get("status"):
            print(f"\r   {data['status']:<60}", end="", flush=True)

    result = await manager.install_model(model_id, progress)
    print()

    if result["success"]:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ {result['message']}")


async def cli_uninstall_model(model_id: str):
    """CLI: Desinstala un modelo"""
    manager = get_model_manager()

    result = await manager.uninstall_model(model_id)

    if result["success"]:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ {result['message']}")


async def cli_show_packs():
    """CLI: Muestra starter packs"""
    manager = get_model_manager()
    packs = manager.get_packs()

    print("\n📦 Starter Packs:\n")

    for pack_id, pack in packs.items():
        print(f"  {pack['name']} ({pack_id})")
        print(f"     {pack['description']}")
        print(f"     Models: {', '.join(pack['models'])}")
        print(f"     Size: {pack['total_size']}")
        print()

    print("   Install with: purma models pack <pack_id>\n")


async def cli_install_pack(pack_id: str):
    """CLI: Instala un starter pack"""
    manager = get_model_manager()

    status = await manager.check_ollama()
    if not status["running"]:
        print(f"❌ {status['message']}")
        return

    packs = manager.get_packs()
    if pack_id not in packs:
        print(f"❌ Pack '{pack_id}' not found")
        print(f"   Available: {', '.join(packs.keys())}")
        return

    pack = packs[pack_id]
    print(f"\n📦 Installing {pack['name']} pack...")
    print(f"   Models: {', '.join(pack['models'])}")
    print(f"   Total size: {pack['total_size']}\n")

    async def progress(data):
        if data.get("status") == "installing_pack":
            print(f"\n   [{data['current']}/{data['total']}] Installing {data['model']}...")
        elif data.get("percent"):
            print(f"\r      Downloading: {data['percent']:.1f}%", end="", flush=True)

    result = await manager.install_pack(pack_id, progress)
    print()

    if result["success"]:
        print(f"\n✅ Pack '{pack['name']}' installed successfully!")
    else:
        print(f"\n⚠️ Some models may have failed to install")


async def cli_recommend():
    """CLI: Recomienda modelos según el sistema"""
    manager = get_model_manager()

    print("\n🔍 Analyzing your system...\n")

    info = await manager.get_system_info()

    print(f"   RAM: {info['ram_total_gb']}GB total, {info['ram_available_gb']}GB available")
    print(f"   GPU: {info['gpu']}")
    print()
    print(f"   📦 Recommended pack: {info['pack_info']['name']}")
    print(f"      {info['pack_info']['description']}")
    print(f"      Models: {', '.join(info['pack_info']['models'])}")
    print()
    print(f"   Install with: purma models pack {info['recommended_pack']}")
    print()


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    import sys

    async def main():
        if len(sys.argv) < 2:
            print("Usage: purma_models.py <command> [args]")
            print("Commands: list, available, install, uninstall, packs, pack, recommend")
            return

        command = sys.argv[1]

        if command == "list":
            await cli_list_models()
        elif command == "available":
            category = sys.argv[2] if len(sys.argv) > 2 else None
            await cli_available_models(category)
        elif command == "install":
            if len(sys.argv) < 3:
                print("Usage: purma_models.py install <model>")
                return
            await cli_install_model(sys.argv[2])
        elif command == "uninstall":
            if len(sys.argv) < 3:
                print("Usage: purma_models.py uninstall <model>")
                return
            await cli_uninstall_model(sys.argv[2])
        elif command == "packs":
            await cli_show_packs()
        elif command == "pack":
            if len(sys.argv) < 3:
                print("Usage: purma_models.py pack <pack_id>")
                return
            await cli_install_pack(sys.argv[2])
        elif command == "recommend":
            await cli_recommend()
        else:
            print(f"Unknown command: {command}")

    asyncio.run(main())
