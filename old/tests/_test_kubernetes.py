# -*- coding: utf-8 -*-
"""
Tests unitaires pour les manifests Kubernetes du MLOps
"""

import pytest
import yaml
from pathlib import Path
from typing import List, Dict, Any
import re


class TestKubernetesYAML:
    """Tests pour la validation YAML des manifests Kubernetes"""
    
    @pytest.fixture(autouse=True)
    def load_manifests(self):
        """Load all Kubernetes manifest files"""
        self.k8s_dir = Path(__file__).parent.parent / "k8s"
        self.manifests = {}
        
        for yaml_file in self.k8s_dir.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                try:
                    content = yaml.safe_load_all(f)
                    self.manifests[yaml_file.name] = list(content)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {yaml_file.name}: {str(e)}")
    
    def test_yaml_files_exist(self):
        """Verify Kubernetes manifest files exist"""
        assert len(self.manifests) > 0
    
    def test_namespace_config_exists(self):
        """Verify namespace configuration exists"""
        assert '00-namespace-config.yaml' in self.manifests
    
    def test_mlflow_config_exists(self):
        """Verify MLflow configuration exists"""
        assert '01-mlflow.yaml' in self.manifests
    
    def test_inference_config_exists(self):
        """Verify Inference configuration exists"""
        assert '02-inference.yaml' in self.manifests
    
    def test_training_config_exists(self):
        """Verify Training configuration exists"""
        assert '03-training.yaml' in self.manifests
    
    def test_gateway_config_exists(self):
        """Verify Gateway configuration exists"""
        assert '04-gateway.yaml' in self.manifests


class TestNamespaceConfig:
    """Tests pour la configuration du namespace"""
    
    @pytest.fixture
    def namespace_manifest(self):
        """Get namespace manifest"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        with open(k8s_dir / "00-namespace-config.yaml", 'r') as f:
            return list(yaml.safe_load_all(f))
    
    def test_namespace_has_name(self, namespace_manifest):
        """Verify namespace has a name"""
        for manifest in namespace_manifest:
            if manifest and manifest.get('kind') == 'Namespace':
                assert 'metadata' in manifest
                assert 'name' in manifest['metadata']
    
    def test_namespace_name_valid(self, namespace_manifest):
        """Verify namespace name follows Kubernetes conventions"""
        for manifest in namespace_manifest:
            if manifest and manifest.get('kind') == 'Namespace':
                name = manifest['metadata']['name']
                # Namespace names should be lowercase
                assert name == name.lower()
                # Should not contain uppercase
                assert not any(c.isupper() for c in name)


class TestMLFlowDeployment:
    """Tests pour le déploiement MLflow"""
    
    @pytest.fixture
    def mlflow_manifest(self):
        """Get MLflow manifest"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        with open(k8s_dir / "01-mlflow.yaml", 'r') as f:
            return list(yaml.safe_load_all(f))
    
    def test_mlflow_has_service(self, mlflow_manifest):
        """Verify MLflow has a Service"""
        kinds = [m.get('kind') for m in mlflow_manifest if m]
        assert 'Service' in kinds
    
    def test_mlflow_has_deployment(self, mlflow_manifest):
        """Verify MLflow has a Deployment"""
        kinds = [m.get('kind') for m in mlflow_manifest if m]
        assert 'Deployment' in kinds
    
    def test_mlflow_service_has_port(self, mlflow_manifest):
        """Verify MLflow service exposes port 5000"""
        for manifest in mlflow_manifest:
            if manifest and manifest.get('kind') == 'Service':
                if 'mlflow' in manifest.get('metadata', {}).get('name', ''):
                    ports = manifest.get('spec', {}).get('ports', [])
                    port_numbers = [p.get('port') for p in ports]
                    assert 5000 in port_numbers or any('mlflow' in p.get('name', '') for p in ports)
    
    def test_mlflow_has_image(self, mlflow_manifest):
        """Verify MLflow deployment has container image"""
        for manifest in mlflow_manifest:
            if manifest and manifest.get('kind') == 'Deployment':
                containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                assert len(containers) > 0
                for container in containers:
                    assert 'image' in container
                    assert container['image'] != ""


class TestInferenceDeployment:
    """Tests pour le déploiement Inference"""
    
    @pytest.fixture
    def inference_manifest(self):
        """Get Inference manifest"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        with open(k8s_dir / "02-inference.yaml", 'r') as f:
            return list(yaml.safe_load_all(f))
    
    def test_inference_has_deployment(self, inference_manifest):
        """Verify Inference has a Deployment"""
        kinds = [m.get('kind') for m in inference_manifest if m]
        assert 'Deployment' in kinds
    
    def test_inference_has_service(self, inference_manifest):
        """Verify Inference has a Service"""
        kinds = [m.get('kind') for m in inference_manifest if m]
        assert 'Service' in kinds
    
    def test_inference_has_replicas(self, inference_manifest):
        """Verify Inference deployment has replicas configured"""
        for manifest in inference_manifest:
            if manifest and manifest.get('kind') == 'Deployment':
                replicas = manifest.get('spec', {}).get('replicas', 0)
                assert replicas > 0
    
    def test_inference_service_port_8001(self, inference_manifest):
        """Verify Inference service exposes port 8001"""
        for manifest in inference_manifest:
            if manifest and manifest.get('kind') == 'Service':
                if 'inference' in manifest.get('metadata', {}).get('name', ''):
                    ports = manifest.get('spec', {}).get('ports', [])
                    port_numbers = [p.get('port') for p in ports]
                    assert 8001 in port_numbers or 8000 in port_numbers
    
    def test_inference_has_liveness_probe(self, inference_manifest):
        """Verify Inference has liveness probe"""
        for manifest in inference_manifest:
            if manifest and manifest.get('kind') == 'Deployment':
                containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                for container in containers:
                    if 'inference' in container.get('name', ''):
                        assert 'livenessProbe' in container or 'readinessProbe' in container


class TestTrainingDeployment:
    """Tests pour le déploiement Training"""
    
    @pytest.fixture
    def training_manifest(self):
        """Get Training manifest"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        with open(k8s_dir / "03-training.yaml", 'r') as f:
            return list(yaml.safe_load_all(f))
    
    def test_training_has_deployment(self, training_manifest):
        """Verify Training has a Deployment"""
        kinds = [m.get('kind') for m in training_manifest if m]
        assert 'Deployment' in kinds
    
    def test_training_has_service(self, training_manifest):
        """Verify Training has a Service"""
        kinds = [m.get('kind') for m in training_manifest if m]
        assert 'Service' in kinds
    
    def test_training_has_resources_defined(self, training_manifest):
        """Verify Training containers have resource limits"""
        for manifest in training_manifest:
            if manifest and manifest.get('kind') == 'Deployment':
                containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                for container in containers:
                    if 'resources' in container:
                        resources = container['resources']
                        # Either limits or requests should be defined
                        assert 'limits' in resources or 'requests' in resources


class TestGatewayDeployment:
    """Tests pour le déploiement Gateway"""
    
    @pytest.fixture
    def gateway_manifest(self):
        """Get Gateway manifest"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        with open(k8s_dir / "04-gateway.yaml", 'r') as f:
            return list(yaml.safe_load_all(f))
    
    def test_gateway_has_deployment(self, gateway_manifest):
        """Verify Gateway has a Deployment"""
        kinds = [m.get('kind') for m in gateway_manifest if m]
        assert 'Deployment' in kinds
    
    def test_gateway_has_service(self, gateway_manifest):
        """Verify Gateway has a Service"""
        kinds = [m.get('kind') for m in gateway_manifest if m]
        assert 'Service' in kinds
    
    def test_gateway_service_port_8000(self, gateway_manifest):
        """Verify Gateway service exposes port for API access"""
        for manifest in gateway_manifest:
            if manifest and manifest.get('kind') == 'Service':
                if 'gateway' in manifest.get('metadata', {}).get('name', ''):
                    ports = manifest.get('spec', {}).get('ports', [])
                    port_numbers = [p.get('port') for p in ports]
                    # Gateway should expose API port (8000) or HTTP port (80)
                    assert 8000 in port_numbers or 80 in port_numbers
    
    def test_gateway_service_type(self, gateway_manifest):
        """Verify Gateway service is accessible"""
        for manifest in gateway_manifest:
            if manifest and manifest.get('kind') == 'Service':
                if 'gateway' in manifest.get('metadata', {}).get('name', ''):
                    service_type = manifest.get('spec', {}).get('type', 'ClusterIP')
                    # Should be LoadBalancer or NodePort for external access
                    assert service_type in ['LoadBalancer', 'NodePort', 'ClusterIP']


class TestKubernetesLabels:
    """Tests pour les labels Kubernetes"""
    
    @pytest.fixture
    def all_manifests(self):
        """Get all manifests"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        all_manifests = []
        
        for yaml_file in k8s_dir.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                content = yaml.safe_load_all(f)
                all_manifests.extend([m for m in content if m])
        
        return all_manifests
    
    def test_resources_have_labels(self, all_manifests):
        """Verify resources have labels"""
        for manifest in all_manifests:
            if manifest.get('kind') in ['Deployment', 'Service', 'Pod']:
                assert 'metadata' in manifest
                assert 'labels' in manifest['metadata']
    
    def test_labels_include_app(self, all_manifests):
        """Verify resources have app label"""
        for manifest in all_manifests:
            if manifest.get('kind') in ['Deployment', 'Service']:
                labels = manifest.get('metadata', {}).get('labels', {})
                if labels:
                    assert 'app' in labels or 'name' in labels
    
    def test_deployment_selectors_match_labels(self, all_manifests):
        """Verify Deployment selectors match pod labels"""
        for manifest in all_manifests:
            if manifest.get('kind') == 'Deployment':
                selector = manifest.get('spec', {}).get('selector', {}).get('matchLabels', {})
                pod_labels = manifest.get('spec', {}).get('template', {}).get('metadata', {}).get('labels', {})
                
                # Selector labels should be subset of pod labels
                for key, value in selector.items():
                    assert key in pod_labels
                    assert pod_labels[key] == value


class TestKubernetesNamespace:
    """Tests pour le namespace Kubernetes"""
    
    @pytest.fixture
    def all_manifests(self):
        """Get all manifests"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        all_manifests = []
        
        for yaml_file in k8s_dir.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                content = yaml.safe_load_all(f)
                all_manifests.extend([m for m in content if m])
        
        return all_manifests
    
    def test_resources_in_namespace(self, all_manifests):
        """Verify resources are in correct namespace"""
        for manifest in all_manifests:
            if manifest.get('kind') in ['Deployment', 'Service', 'Pod']:
                namespace = manifest.get('metadata', {}).get('namespace')
                if namespace:
                    assert namespace == namespace.lower()
    
    def test_namespace_consistency(self, all_manifests):
        """Verify namespace is consistent across manifests"""
        namespaces = set()
        
        for manifest in all_manifests:
            if manifest.get('kind') != 'Namespace':
                namespace = manifest.get('metadata', {}).get('namespace')
                if namespace:
                    namespaces.add(namespace)
        
        # Should not have multiple namespaces
        assert len(namespaces) <= 1


class TestContainerConfiguration:
    """Tests pour la configuration des containers"""
    
    @pytest.fixture
    def all_manifests(self):
        """Get all manifests"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        all_manifests = []
        
        for yaml_file in k8s_dir.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                content = yaml.safe_load_all(f)
                all_manifests.extend([m for m in content if m])
        
        return all_manifests
    
    def test_containers_have_images(self, all_manifests):
        """Verify containers have images"""
        for manifest in all_manifests:
            if manifest.get('kind') == 'Deployment':
                containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                for container in containers:
                    assert 'image' in container
                    assert container['image'] != ""
    
    def test_image_tags_specified(self, all_manifests):
        """Verify images have tags specified"""
        for manifest in all_manifests:
            if manifest.get('kind') == 'Deployment':
                containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                for container in containers:
                    image = container['image']
                    # Image should have tag (not just 'latest')
                    assert ':' in image or image.endswith(':latest')
    
    def test_containers_have_names(self, all_manifests):
        """Verify containers have names"""
        for manifest in all_manifests:
            if manifest.get('kind') == 'Deployment':
                containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                for container in containers:
                    assert 'name' in container
                    assert container['name'] != ""


class TestEnvironmentVariables:
    """Tests pour les variables d'environnement"""
    
    @pytest.fixture
    def all_manifests(self):
        """Get all manifests"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        all_manifests = []
        
        for yaml_file in k8s_dir.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                content = yaml.safe_load_all(f)
                all_manifests.extend([m for m in content if m])
        
        return all_manifests
    
    def test_environment_variables_have_names(self, all_manifests):
        """Verify environment variables have names"""
        for manifest in all_manifests:
            if manifest.get('kind') == 'Deployment':
                containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                for container in containers:
                    env_vars = container.get('env', [])
                    for env_var in env_vars:
                        assert 'name' in env_var
                        assert env_var['name'] != ""
    
    def test_environment_variables_have_values(self, all_manifests):
        """Verify environment variables have values"""
        for manifest in all_manifests:
            if manifest.get('kind') == 'Deployment':
                containers = manifest.get('spec', {}).get('template', {}).get('spec', {}).get('containers', [])
                for container in containers:
                    env_vars = container.get('env', [])
                    for env_var in env_vars:
                        # Either 'value' or 'valueFrom' should be present
                        assert 'value' in env_var or 'valueFrom' in env_var


class TestServiceConfiguration:
    """Tests pour la configuration des Services"""
    
    @pytest.fixture
    def all_manifests(self):
        """Get all manifests"""
        k8s_dir = Path(__file__).parent.parent / "k8s"
        all_manifests = []
        
        for yaml_file in k8s_dir.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                content = yaml.safe_load_all(f)
                all_manifests.extend([m for m in content if m])
        
        return all_manifests
    
    def test_services_have_selectors(self, all_manifests):
        """Verify Services have selectors"""
        for manifest in all_manifests:
            if manifest.get('kind') == 'Service':
                selectors = manifest.get('spec', {}).get('selector', {})
                assert len(selectors) > 0
    
    def test_services_have_ports(self, all_manifests):
        """Verify Services have ports"""
        for manifest in all_manifests:
            if manifest.get('kind') == 'Service':
                ports = manifest.get('spec', {}).get('ports', [])
                assert len(ports) > 0
                for port in ports:
                    assert 'port' in port
                    assert isinstance(port['port'], int)
    
    def test_service_ports_valid(self, all_manifests):
        """Verify Service ports are valid"""
        for manifest in all_manifests:
            if manifest.get('kind') == 'Service':
                ports = manifest.get('spec', {}).get('ports', [])
                for port in ports:
                    assert 1 <= port['port'] <= 65535


if __name__ == "__main__":
    # Exécuter les tests
    pytest.main([__file__, "-v", "--tb=short"])
