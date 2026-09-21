# Anti-Fraud Verification with TEE and ZK-Proofs

## Table of Contents
1. [Overview](#overview)
2. [Intel SGX Setup and Attestation](#intel-sgx-setup-and-attestation)
3. [AMD SEV-SNP Configuration](#amd-sev-snp-configuration)
4. [ZK-Proof System Selection](#zk-proof-system-selection)
5. [Hardware Attestation](#hardware-attestation)
6. [Example Implementations](#example-implementations)
7. [Security Guarantees](#security-guarantees)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Preventing fraud in a decentralized compute marketplace requires cryptographic proof that benchmarks execute on genuine hardware in unmodified environments. This guide covers Trusted Execution Environments (TEEs) and Zero-Knowledge Proofs (ZK-proofs) for verifiable computation.

### Fraud Vectors in Compute Marketplaces

**Common Fraud Attempts**:
1. **Virtualized Hardware**: Provider claims bare metal but runs VMs
2. **Benchmark Spoofing**: Modified benchmark binaries return fake scores
3. **Result Manipulation**: Altered benchmark outputs
4. **Hardware Misrepresentation**: Claiming better hardware than available
5. **Time-Sharing**: Multiple "dedicated" instances on same hardware
6. **Overcommitment**: More resources sold than physically available

### Defense Mechanisms

| Mechanism | Purpose | Strength | Limitations |
|-----------|---------|----------|-------------|
| TEE (SGX/SEV-SNP) | Secure execution | Very High | Hardware dependency |
| Remote Attestation | Prove TEE authenticity | High | Requires trust in CPU vendor |
| ZK-Proofs | Prove computation correctness | High | Computational overhead |
| VM Detection | Identify virtualization | Medium | Can be bypassed |
| Timing Analysis | Detect inconsistencies | Medium | Environmental noise |
| Statistical Analysis | Pattern detection | Medium | Requires history |

### Recommended Approach

**Multi-Layer Defense**:
1. **Primary**: TEE-based execution with remote attestation
2. **Secondary**: ZK-proofs for computation verification
3. **Tertiary**: Statistical anomaly detection
4. **Quaternary**: VM detection heuristics

---

## Intel SGX Setup and Attestation

### Intel SGX Overview

Intel Software Guard Extensions (SGX) creates hardware-protected memory regions called enclaves where code executes with confidentiality and integrity guarantees.

**Key Features**:
- Hardware-enforced memory encryption
- Remote attestation via ECDSA signatures
- Sealed storage for persistent secrets
- Side-channel protections (newer CPUs)

### Important Note on SGX Deprecation

Intel has announced that SGX attestation services (Intel Attestation Service - IAS) will be discontinued in April 2025. New deployments should use:

1. **Intel SGX DCAP (Data Center Attestation Primitives)** for Intel CPUs
2. **AMD SEV-SNP** for AMD CPUs (recommended for new deployments)
3. **Hybrid approach** supporting both

### Hardware Requirements

**CPU Requirements**:
- Intel Xeon E3, E5, SP (Scalable Processors)
- SGX support enabled in BIOS
- SGX version 2 recommended (better performance)

**Memory Requirements**:
- EPC (Enclave Page Cache): 128 MB minimum (configurable in BIOS)
- Larger EPC for better performance

### Check SGX Support

```bash
#!/bin/bash
# check_sgx_support.sh

echo "=== Checking Intel SGX Support ==="

# Check CPU support
if grep -q sgx /proc/cpuinfo; then
    echo "✓ CPU supports SGX"
else
    echo "✗ CPU does not support SGX"
    exit 1
fi

# Check if SGX is enabled
if [ -c /dev/sgx_enclave ] && [ -c /dev/sgx_provision ]; then
    echo "✓ SGX devices present"
else
    echo "✗ SGX devices not found (may need to enable in BIOS)"
fi

# Check SGX driver
if lsmod | grep -q intel_sgx; then
    echo "✓ SGX driver loaded"
else
    echo "✗ SGX driver not loaded"
fi

# Get EPC size
if [ -f /sys/firmware/efi/runtime-map/sgx_epc ]; then
    EPC_SIZE=$(cat /sys/firmware/efi/runtime-map/sgx_epc | wc -c)
    echo "EPC Size: $((EPC_SIZE / 1024 / 1024)) MB"
fi

# Check for SGX SDK
if command -v sgx-detect &> /dev/null; then
    echo ""
    sgx-detect
fi
```

### Install Intel SGX SDK and PSW

```bash
#!/bin/bash
# install_sgx.sh

set -e

echo "Installing Intel SGX SDK and Platform Software (PSW)..."

# Add Intel SGX repository
echo 'deb [arch=amd64] https://download.01.org/intel-sgx/sgx_repo/ubuntu jammy main' | \
    sudo tee /etc/apt/sources.list.d/intel-sgx.list
wget -qO - https://download.01.org/intel-sgx/sgx_repo/ubuntu/intel-sgx-deb.key | \
    sudo apt-key add -

sudo apt-get update

# Install SGX driver (if not in kernel)
sudo apt-get install -y sgx-aesm-service libsgx-aesm-launch-plugin

# Install DCAP libraries for attestation
sudo apt-get install -y \
    libsgx-dcap-ql \
    libsgx-dcap-default-qpl \
    libsgx-dcap-quote-verify \
    libsgx-urts \
    libsgx-uae-service

# Install development tools
sudo apt-get install -y \
    libsgx-enclave-common-dev \
    libsgx-dcap-ql-dev \
    libsgx-dcap-default-qpl-dev

# Start AESM service
sudo systemctl enable aesmd
sudo systemctl start aesmd

echo "✓ Intel SGX installed successfully"

# Verify installation
systemctl status aesmd
```

### Gramine LibOS for Running Applications in SGX

Gramine is a Library OS that runs unmodified Linux applications in SGX enclaves.

```bash
#!/bin/bash
# install_gramine.sh

set -e

echo "Installing Gramine..."

# Install dependencies
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    autoconf \
    bison \
    gawk \
    nasm \
    python3-click \
    python3-jinja2 \
    python3-pyelftools \
    python3-toml \
    wget

# Install Gramine from package
sudo curl -fsSLo /usr/share/keyrings/gramine-keyring.gpg https://packages.gramineproject.io/gramine-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gramine-keyring.gpg] https://packages.gramineproject.io/ $(lsb_release -sc) main" | \
    sudo tee /etc/apt/sources.list.d/gramine.list

sudo apt-get update
sudo apt-get install -y gramine

# Verify installation
gramine-sgx --version

echo "✓ Gramine installed successfully"
```

### Create SGX Manifest for Benchmark

```toml
# benchmark.manifest.template
loader.entrypoint = "file:{{ gramine.libos }}"
libos.entrypoint = "{{ entrypoint }}"

loader.log_level = "{{ log_level }}"

loader.env.LD_LIBRARY_PATH = "/lib:{{ arch_libdir }}:/usr/lib:/usr/{{ arch_libdir }}"

# Allow benchmark to use multiple threads
loader.env.OMP_NUM_THREADS = "{{ num_threads }}"

# Mount necessary filesystems
fs.mounts = [
  { path = "/lib", uri = "file:{{ gramine.runtimedir() }}" },
  { path = "{{ arch_libdir }}", uri = "file:{{ arch_libdir }}" },
  { path = "/usr", uri = "file:/usr" },
  { path = "/tmp", type = "tmpfs" },
  { path = "/results", uri = "file:/var/benchmark/results", type = "chroot" },
  { path = "/data", uri = "file:/data/mlperf", type = "chroot" },
]

# SGX configuration
sgx.debug = false
sgx.edmm_enable = {{ 'true' if env.get('EDMM', '0') == '1' else 'false' }}
sgx.enclave_size = "{{ enclave_size }}"
sgx.max_threads = {{ max_threads }}
sgx.isvprodid = 1
sgx.isvsvn = 1

# Enable remote attestation
sgx.remote_attestation = "dcap"

# Trusted files (will be measured in attestation)
sgx.trusted_files = [
  "file:{{ entrypoint }}",
  "file:{{ gramine.libos }}",
  "file:{{ gramine.runtimedir() }}/",
  "file:{{ arch_libdir }}/",
  "file:/usr/lib/x86_64-linux-gnu/",
  "file:/usr/bin/",
]

# Allowed files (can be accessed but not measured)
sgx.allowed_files = [
  "file:/tmp",
  "file:/results",
  "file:/data",
]
```

### Remote Attestation with SGX DCAP

```python
# sgx_attestation.py
import struct
import hashlib
import json
from typing import Dict, Tuple, Optional
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

class SGXAttestation:
    """Handle Intel SGX DCAP attestation."""

    # SGX quote structure constants
    QUOTE_HEADER_SIZE = 48
    REPORT_BODY_SIZE = 384

    def __init__(self, pccs_url: Optional[str] = None):
        """
        Initialize SGX attestation handler.

        Args:
            pccs_url: Provisioning Certificate Caching Service URL
                     (default: Intel's PCS)
        """
        self.pccs_url = pccs_url or "https://api.trustedservices.intel.com/sgx"

    def generate_quote(self, report_data: bytes) -> bytes:
        """
        Generate SGX quote (attestation report).

        Args:
            report_data: Custom data to include in quote (64 bytes)

        Returns:
            SGX quote (binary)
        """
        # This is a simplified example
        # Actual implementation uses SGX SDK functions

        # In real implementation:
        # 1. Create target_info for QE (Quoting Enclave)
        # 2. Generate report with sgx_create_report()
        # 3. Request quote from QE with sgx_get_quote()

        # For demonstration:
        import subprocess

        # Use Gramine's quote generation
        result = subprocess.run(
            ["gramine-sgx-quote", "--report-data", report_data.hex()],
            capture_output=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Quote generation failed: {result.stderr}")

        return result.stdout

    def verify_quote(
        self,
        quote: bytes,
        expected_mrenclave: Optional[bytes] = None,
        expected_mrsigner: Optional[bytes] = None
    ) -> Dict:
        """
        Verify SGX quote and extract claims.

        Args:
            quote: SGX quote to verify
            expected_mrenclave: Expected enclave measurement (optional)
            expected_mrsigner: Expected signer identity (optional)

        Returns:
            Dictionary with verification results and extracted claims
        """
        # Parse quote structure
        header = quote[:self.QUOTE_HEADER_SIZE]
        report_body = quote[self.QUOTE_HEADER_SIZE:self.QUOTE_HEADER_SIZE + self.REPORT_BODY_SIZE]

        # Extract version and attestation key type
        version = struct.unpack('<H', header[0:2])[0]
        att_key_type = struct.unpack('<H', header[2:4])[0]

        # Parse report body
        cpu_svn = report_body[0:16]
        misc_select = struct.unpack('<I', report_body[16:20])[0]
        attributes = report_body[48:64]
        mrenclave = report_body[64:96]
        mrsigner = report_body[128:160]
        isv_prod_id = struct.unpack('<H', report_body[256:258])[0]
        isv_svn = struct.unpack('<H', report_body[258:260])[0]
        report_data = report_body[320:384]

        # Verify measurements if provided
        verification_result = {
            "valid": True,
            "errors": []
        }

        if expected_mrenclave and mrenclave != expected_mrenclave:
            verification_result["valid"] = False
            verification_result["errors"].append(
                f"MRENCLAVE mismatch: got {mrenclave.hex()}, expected {expected_mrenclave.hex()}"
            )

        if expected_mrsigner and mrsigner != expected_mrsigner:
            verification_result["valid"] = False
            verification_result["errors"].append(
                f"MRSIGNER mismatch: got {mrsigner.hex()}, expected {expected_mrsigner.hex()}"
            )

        # Verify quote signature (simplified)
        # Real implementation would:
        # 1. Extract certification chain from quote
        # 2. Verify chain back to Intel root CA
        # 3. Verify quote signature with certified key
        # 4. Check TCB (Trusted Computing Base) status

        return {
            "verification": verification_result,
            "claims": {
                "version": version,
                "mrenclave": mrenclave.hex(),
                "mrsigner": mrsigner.hex(),
                "isv_prod_id": isv_prod_id,
                "isv_svn": isv_svn,
                "cpu_svn": cpu_svn.hex(),
                "attributes": attributes.hex(),
                "report_data": report_data.hex()
            }
        }

    def verify_quote_with_dcap(self, quote: bytes) -> Dict:
        """
        Verify SGX quote using DCAP libraries.

        This calls the Intel DCAP quote verification library.
        """
        import ctypes

        # Load DCAP quote verification library
        try:
            libdcap = ctypes.CDLL("libsgx_dcap_quoteverify.so")
        except OSError:
            raise RuntimeError("SGX DCAP library not installed")

        # Call sgx_qv_verify_quote()
        # (Simplified - actual implementation more complex)

        quote_buf = ctypes.create_string_buffer(quote)
        quote_size = len(quote)

        # Collateral (cert chains, CRLs, etc.) obtained from PCCS
        collateral = self._fetch_collateral(quote)

        # Verify quote
        verification_result = libdcap.sgx_qv_verify_quote(
            quote_buf,
            quote_size,
            collateral
        )

        return {
            "valid": verification_result == 0,
            "result_code": verification_result
        }

    def _fetch_collateral(self, quote: bytes) -> Dict:
        """Fetch certification collateral from PCCS."""
        # Extract FMSPC and other identifiers from quote
        # Query PCCS for certification data
        # Return collateral for verification
        pass


# Example usage
if __name__ == "__main__":
    attestation = SGXAttestation()

    # Custom data to include in quote (e.g., hash of benchmark results)
    benchmark_hash = hashlib.sha256(b"benchmark_results").digest()
    report_data = benchmark_hash + b'\x00' * (64 - len(benchmark_hash))

    # Generate quote
    print("Generating SGX quote...")
    quote = attestation.generate_quote(report_data)
    print(f"Quote size: {len(quote)} bytes")

    # Verify quote
    print("\nVerifying quote...")
    result = attestation.verify_quote(quote)

    print(f"Valid: {result['verification']['valid']}")
    print(f"MRENCLAVE: {result['claims']['mrenclave']}")
    print(f"MRSIGNER: {result['claims']['mrsigner']}")
```

### Run Benchmark in SGX Enclave

```python
# sgx_benchmark_runner.py
import subprocess
import hashlib
import json
from pathlib import Path

class SGXBenchmarkRunner:
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        self.attestation = SGXAttestation()

    def run_benchmark(self, benchmark_binary: str, args: list) -> Dict:
        """
        Run benchmark in SGX enclave and generate attestation.

        Args:
            benchmark_binary: Path to benchmark executable
            args: Command-line arguments

        Returns:
            Dictionary with results and attestation
        """
        # Generate benchmark execution manifest
        self._prepare_manifest(benchmark_binary)

        # Run in SGX
        print(f"Running {benchmark_binary} in SGX enclave...")

        cmd = ["gramine-sgx", self.manifest_path] + args

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Benchmark failed: {result.stderr}")

        # Parse benchmark output
        benchmark_results = json.loads(result.stdout)

        # Generate attestation
        results_hash = hashlib.sha256(
            json.dumps(benchmark_results, sort_keys=True).encode()
        ).digest()

        report_data = results_hash + b'\x00' * (64 - len(results_hash))

        quote = self.attestation.generate_quote(report_data)

        return {
            "results": benchmark_results,
            "attestation": {
                "quote": quote.hex(),
                "report_data": report_data.hex(),
                "results_hash": results_hash.hex()
            }
        }

    def _prepare_manifest(self, benchmark_binary: str):
        """Generate Gramine manifest for benchmark."""
        # Use manifest template and fill in values
        template = Path(self.manifest_path + ".template").read_text()

        manifest_content = template.format(
            entrypoint=benchmark_binary,
            enclave_size="4G",
            max_threads=128,
            log_level="error"
        )

        Path(self.manifest_path).write_text(manifest_content)

        # Sign manifest
        subprocess.run(
            ["gramine-sgx-sign", "--manifest", self.manifest_path, "--output", self.manifest_path + ".sgx"],
            check=True
        )


# Example usage
if __name__ == "__main__":
    runner = SGXBenchmarkRunner(manifest_path="/opt/benchmarks/geekbench.manifest")

    result = runner.run_benchmark(
        benchmark_binary="/usr/local/bin/geekbench6",
        args=["--no-upload", "--output-format", "json"]
    )

    print("Benchmark complete")
    print(f"Score: {result['results']['score']}")
    print(f"Attestation quote: {result['attestation']['quote'][:64]}...")
```

---

## AMD SEV-SNP Configuration

### AMD SEV-SNP Overview

AMD Secure Encrypted Virtualization - Secure Nested Paging (SEV-SNP) provides VM-level confidential computing with memory encryption and integrity protection.

**Key Features**:
- Entire VM memory encrypted
- Protection against hypervisor attacks
- Remote attestation
- Better performance than SGX (no EPC limitations)
- Recommended for new deployments

### Hardware Requirements

- AMD EPYC 3rd Gen (Milan) or newer
- SEV-SNP enabled in BIOS
- Compatible hypervisor (KVM with SEV support)

### Check SEV-SNP Support

```bash
#!/bin/bash
# check_sev_snp.sh

echo "=== Checking AMD SEV-SNP Support ==="

# Check CPU support
if grep -q sev /proc/cpuinfo; then
    echo "✓ CPU supports SEV"
else
    echo "✗ CPU does not support SEV"
    exit 1
fi

# Check for SEV-SNP
if [ -f /sys/module/kvm_amd/parameters/sev_snp ]; then
    SNP_ENABLED=$(cat /sys/module/kvm_amd/parameters/sev_snp)
    if [ "$SNP_ENABLED" == "Y" ]; then
        echo "✓ SEV-SNP enabled"
    else
        echo "✗ SEV-SNP disabled"
    fi
else
    echo "✗ SEV-SNP not available"
fi

# Check /dev/sev
if [ -c /dev/sev ]; then
    echo "✓ SEV device present"
else
    echo "✗ SEV device not found"
fi

# Get SEV capabilities
if command -v sevctl &> /dev/null; then
    sevctl show capabilities
fi
```

### Install SEV-SNP Tools

```bash
#!/bin/bash
# install_sev_snp.sh

set -e

echo "Installing AMD SEV-SNP tools..."

# Install dependencies
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    libssl-dev \
    uuid-dev \
    git

# Install sevctl tool
git clone https://github.com/AMDESE/sev-tool.git
cd sev-tool
make
sudo make install

# Install snpguest tool for attestation
cargo install snpguest

echo "✓ SEV-SNP tools installed"
```

### AMD SEV-SNP Attestation

```python
# sev_snp_attestation.py
import subprocess
import json
import requests
from typing import Dict
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

class SEVSNPAttestation:
    """Handle AMD SEV-SNP attestation."""

    AMD_ASK_URL = "https://kdsintf.amd.com/vcek/v1"

    def __init__(self):
        pass

    def generate_report(self, report_data: bytes) -> bytes:
        """
        Generate SEV-SNP attestation report.

        Args:
            report_data: Custom data to include (64 bytes)

        Returns:
            Attestation report (binary)
        """
        # Use snpguest to generate report
        result = subprocess.run(
            ["snpguest", "report", report_data.hex(), "/tmp/attestation_report.bin"],
            capture_output=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Report generation failed: {result.stderr}")

        with open("/tmp/attestation_report.bin", "rb") as f:
            return f.read()

    def verify_report(
        self,
        report: bytes,
        expected_measurement: bytes = None
    ) -> Dict:
        """
        Verify SEV-SNP attestation report.

        Args:
            report: SEV-SNP attestation report
            expected_measurement: Expected launch measurement

        Returns:
            Verification results and claims
        """
        # Parse report structure
        # SEV-SNP report is 1184 bytes
        if len(report) < 1184:
            raise ValueError("Invalid report size")

        # Extract fields
        version = int.from_bytes(report[0:4], 'little')
        guest_svn = int.from_bytes(report[4:8], 'little')
        policy = int.from_bytes(report[8:16], 'little')

        # Launch measurement (48 bytes)
        measurement = report[48:96]

        # Report data (64 bytes)
        report_data = report[96:160]

        # Signature (512 bytes starting at offset 672)
        signature = report[672:1184]

        # Verify signature
        # In production, would:
        # 1. Fetch VCEK certificate from AMD KDS
        # 2. Verify certificate chain
        # 3. Verify report signature

        verification_result = {
            "valid": True,  # Placeholder
            "errors": []
        }

        if expected_measurement and measurement != expected_measurement:
            verification_result["valid"] = False
            verification_result["errors"].append(
                f"Measurement mismatch: got {measurement.hex()}, expected {expected_measurement.hex()}"
            )

        return {
            "verification": verification_result,
            "claims": {
                "version": version,
                "guest_svn": guest_svn,
                "policy": policy,
                "measurement": measurement.hex(),
                "report_data": report_data.hex()
            }
        }

    def fetch_vcek_certificate(self, report: bytes) -> bytes:
        """
        Fetch VCEK (Versioned Chip Endorsement Key) certificate from AMD.

        Args:
            report: SEV-SNP report containing chip ID

        Returns:
            VCEK certificate
        """
        # Extract chip ID from report
        chip_id = report[384:448].hex()

        # Construct URL
        url = f"{self.AMD_ASK_URL}/{chip_id}"

        response = requests.get(url)
        response.raise_for_status()

        return response.content

    def verify_with_vcek(self, report: bytes) -> bool:
        """
        Verify report signature using VCEK certificate.

        Args:
            report: SEV-SNP attestation report

        Returns:
            True if signature valid
        """
        # Fetch VCEK
        vcek_cert = self.fetch_vcek_certificate(report)

        # Verify signature
        # (Actual implementation would use cryptography library)

        return True


# Example usage
if __name__ == "__main__":
    attestation = SEVSNPAttestation()

    # Generate report
    import hashlib
    benchmark_hash = hashlib.sha256(b"benchmark_results").digest()
    report_data = benchmark_hash + b'\x00' * (64 - len(benchmark_hash))

    print("Generating SEV-SNP attestation report...")
    report = attestation.generate_report(report_data)

    print(f"Report size: {len(report)} bytes")

    # Verify report
    print("\nVerifying report...")
    result = attestation.verify_report(report)

    print(f"Valid: {result['verification']['valid']}")
    print(f"Measurement: {result['claims']['measurement']}")
```

### Launch VM with SEV-SNP

```bash
#!/bin/bash
# launch_sev_snp_vm.sh

# Create QEMU command for SEV-SNP VM
qemu-system-x86_64 \
    -enable-kvm \
    -cpu EPYC-v4 \
    -machine q35,confidential-guest-support=sev0,memory-backend=ram1 \
    -object memory-backend-memfd,id=ram1,size=8G,share=true \
    -object sev-snp-guest,id=sev0,cbitpos=51,reduced-phys-bits=1 \
    -m 8G \
    -smp 4 \
    -drive file=/path/to/disk.qcow2,if=virtio \
    -nographic
```

---

## ZK-Proof System Selection

### Overview of ZK-Proof Systems for Hardware Verification

Zero-Knowledge Proofs allow proving computation correctness without revealing inputs or intermediate states.

**Popular ZK Systems (2025)**:

| System | Type | Proof Size | Verification Time | Prover Time | Best For |
|--------|------|------------|-------------------|-------------|----------|
| Groth16 | zk-SNARK | ~200 bytes | ~1 ms | Minutes | Fixed circuits |
| PLONK | zk-SNARK | ~1 KB | ~10 ms | Minutes | Flexible circuits |
| STARKs | zk-STARK | ~100 KB | ~100 ms | Seconds | Transparency |
| Halo2 | Recursive | ~50 KB | ~50 ms | Minutes | Recursive proofs |
| RISC Zero | zkVM | Variable | Variable | Variable | General computation |
| SP1 | zkVM | Variable | Variable | Fast | High performance |

### Recommended: RISC Zero for Benchmark Verification

RISC Zero provides a general-purpose zkVM that can prove arbitrary RISC-V programs.

**Advantages**:
- No need to write circuits
- Prove existing benchmark binaries
- Strong security guarantees
- Active development

```bash
# Install RISC Zero
curl -L https://risczero.com/install | bash
rzup install
```

### Example: Prove Benchmark Execution with RISC Zero

```rust
// guest/src/main.rs (runs in zkVM)
#![no_main]
risc0_zkvm::guest::entry!(main);

use risc0_zkvm::guest::env;

pub fn main() {
    // Read benchmark input
    let input: BenchmarkInput = env::read();

    // Run benchmark
    let result = run_geekbench_benchmark(&input);

    // Commit result (makes it public)
    env::commit(&result);
}

fn run_geekbench_benchmark(input: &BenchmarkInput) -> BenchmarkResult {
    // Execute benchmark logic
    // This proves the computation was done correctly
    // without revealing intermediate values

    BenchmarkResult {
        score: 1523,
        multi_core: 18945,
        // ... other metrics
    }
}
```

```rust
// host/src/main.rs (generates proof)
use risc0_zkvm::{default_prover, ExecutorEnv};

fn main() {
    // Setup environment
    let env = ExecutorEnv::builder()
        .write(&benchmark_input)
        .unwrap()
        .build()
        .unwrap();

    // Generate proof
    let prover = default_prover();
    let receipt = prover.prove(env, BENCHMARK_ELF).unwrap();

    // Extract result
    let result: BenchmarkResult = receipt.journal.decode().unwrap();

    // Verify proof
    receipt.verify(BENCHMARK_ID).unwrap();

    println!("Proof generated and verified!");
    println!("Benchmark score: {}", result.score);
}
```

### Alternative: SP1 zkVM

SP1 is a high-performance zkVM alternative:

```bash
# Install SP1
curl -L https://sp1.succinct.xyz | bash
sp1up
```

```rust
// SP1 example
use sp1_zkvm::precompiles::io::*;

fn main() {
    // Read benchmark input
    let input = sp1_zkvm::io::read::<BenchmarkInput>();

    // Execute benchmark
    let result = execute_benchmark(&input);

    // Commit result
    sp1_zkvm::io::commit(&result);
}
```

---

## Hardware Attestation

### Combined TEE + ZK Approach

**Optimal Security Model**:

```
┌────────────────────────────────────────────────────────────┐
│                    Provider Node                           │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          TEE (SGX/SEV-SNP)                          │  │
│  │                                                      │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │  Benchmark Execution                           │ │  │
│  │  │  • Geekbench 6                                 │ │  │
│  │  │  • Results: {score: 1523, multi: 18945}       │ │  │
│  │  └────────────────┬───────────────────────────────┘ │  │
│  │                   │                                  │  │
│  │                   ▼                                  │  │
│  │  ┌────────────────────────────────────────────────┐ │  │
│  │  │  Generate TEE Attestation                      │ │  │
│  │  │  • Quote includes results hash                 │ │  │
│  │  │  • Signed by CPU                               │ │  │
│  │  └────────────────┬───────────────────────────────┘ │  │
│  └───────────────────┼──────────────────────────────────┘  │
│                      │                                      │
│                      ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ZK Proof Generation                                 │  │
│  │  • Prove computation correctness                     │  │
│  │  • Input: benchmark parameters                       │  │
│  │  • Output: benchmark results                         │  │
│  └──────────────────┬───────────────────────────────────┘  │
│                     │                                       │
└─────────────────────┼───────────────────────────────────────┘
                      │
                      ▼
          ┌───────────────────────┐
          │  Marketplace Verifier │
          │                       │
          │  1. Verify TEE Quote  │
          │  2. Verify ZK Proof   │
          │  3. Check consistency │
          └───────────────────────┘
```

### Implementation

```python
# combined_attestation.py
from typing import Dict
import json

class CombinedAttestation:
    """Combined TEE and ZK-proof attestation."""

    def __init__(self):
        # Choose TEE based on hardware
        if self._has_sgx():
            self.tee = SGXAttestation()
            self.tee_type = "SGX"
        elif self._has_sev_snp():
            self.tee = SEVSNPAttestation()
            self.tee_type = "SEV-SNP"
        else:
            raise RuntimeError("No supported TEE found")

    def generate_attestation(
        self,
        benchmark_results: Dict
    ) -> Dict:
        """
        Generate combined TEE + ZK attestation.

        Args:
            benchmark_results: Benchmark output

        Returns:
            Combined attestation package
        """
        import hashlib

        # Generate results hash
        results_json = json.dumps(benchmark_results, sort_keys=True)
        results_hash = hashlib.sha256(results_json.encode()).digest()

        # Generate TEE attestation
        report_data = results_hash + b'\x00' * (64 - len(results_hash))

        if self.tee_type == "SGX":
            tee_quote = self.tee.generate_quote(report_data)
        else:
            tee_quote = self.tee.generate_report(report_data)

        # Generate ZK proof (if zkVM available)
        zk_proof = self._generate_zk_proof(benchmark_results)

        return {
            "tee": {
                "type": self.tee_type,
                "quote": tee_quote.hex(),
                "report_data": report_data.hex()
            },
            "zk": {
                "proof": zk_proof["proof"],
                "public_inputs": zk_proof["public_inputs"]
            },
            "results_hash": results_hash.hex(),
            "results": benchmark_results
        }

    def verify_attestation(
        self,
        attestation: Dict
    ) -> Dict:
        """
        Verify combined attestation.

        Args:
            attestation: Attestation package

        Returns:
            Verification results
        """
        results = {
            "valid": False,
            "tee_valid": False,
            "zk_valid": False,
            "errors": []
        }

        # Verify results hash
        results_json = json.dumps(attestation["results"], sort_keys=True)
        computed_hash = hashlib.sha256(results_json.encode()).hexdigest()

        if computed_hash != attestation["results_hash"]:
            results["errors"].append("Results hash mismatch")
            return results

        # Verify TEE attestation
        try:
            tee_quote = bytes.fromhex(attestation["tee"]["quote"])

            if attestation["tee"]["type"] == "SGX":
                tee_result = self.tee.verify_quote(tee_quote)
            else:
                tee_result = self.tee.verify_report(tee_quote)

            results["tee_valid"] = tee_result["verification"]["valid"]

            if not results["tee_valid"]:
                results["errors"].extend(tee_result["verification"]["errors"])

        except Exception as e:
            results["errors"].append(f"TEE verification failed: {e}")

        # Verify ZK proof
        try:
            zk_valid = self._verify_zk_proof(
                attestation["zk"]["proof"],
                attestation["zk"]["public_inputs"]
            )

            results["zk_valid"] = zk_valid

            if not zk_valid:
                results["errors"].append("ZK proof invalid")

        except Exception as e:
            results["errors"].append(f"ZK verification failed: {e}")

        # Overall validity
        results["valid"] = results["tee_valid"] and results["zk_valid"]

        return results

    def _has_sgx(self) -> bool:
        """Check if SGX is available."""
        try:
            with open("/proc/cpuinfo", "r") as f:
                return "sgx" in f.read()
        except:
            return False

    def _has_sev_snp(self) -> bool:
        """Check if SEV-SNP is available."""
        import os
        return os.path.exists("/dev/sev")

    def _generate_zk_proof(self, benchmark_results: Dict) -> Dict:
        """Generate ZK proof of benchmark execution."""
        # Placeholder - actual implementation would use RISC Zero or SP1
        return {
            "proof": "proof_data_here",
            "public_inputs": {
                "score": benchmark_results.get("score"),
                "multi_core": benchmark_results.get("multicore_score")
            }
        }

    def _verify_zk_proof(self, proof: str, public_inputs: Dict) -> bool:
        """Verify ZK proof."""
        # Placeholder - actual implementation would verify with zkVM
        return True


# Example usage
if __name__ == "__main__":
    attestation = CombinedAttestation()

    # Benchmark results
    results = {
        "score": 1523,
        "multicore_score": 18945,
        "timestamp": "2025-10-14T10:30:00Z"
    }

    # Generate attestation
    print("Generating combined attestation...")
    attestation_package = attestation.generate_attestation(results)

    print(f"TEE Type: {attestation_package['tee']['type']}")
    print(f"Results Hash: {attestation_package['results_hash']}")

    # Verify attestation
    print("\nVerifying attestation...")
    verification = attestation.verify_attestation(attestation_package)

    print(f"Valid: {verification['valid']}")
    print(f"TEE Valid: {verification['tee_valid']}")
    print(f"ZK Valid: {verification['zk_valid']}")

    if verification['errors']:
        print("\nErrors:")
        for error in verification['errors']:
            print(f"  - {error}")
```

---

## Security Guarantees

### TEE Security Properties

**Intel SGX**:
- ✓ Memory encryption (AES-128)
- ✓ Integrity protection (MAC)
- ✓ Remote attestation
- ✗ Limited EPC size
- ✗ Side-channel vulnerabilities
- ✗ Requires trust in Intel

**AMD SEV-SNP**:
- ✓ Full VM memory encryption
- ✓ Integrity protection (VMPL)
- ✓ Remote attestation
- ✓ No EPC limitations
- ✓ Protection from hypervisor
- ✗ Requires trust in AMD

### ZK-Proof Security Properties

- ✓ Computational soundness (cannot fake proofs)
- ✓ Zero-knowledge (no information leakage)
- ✓ Verifiable by anyone
- ✓ No trust in hardware vendor
- ✗ High computational cost
- ✗ Proof generation time

### Combined Security Model

**Threat Model**:
1. **Malicious Provider**: Cannot fake benchmark results
2. **Compromised Hypervisor**: TEE protects execution
3. **Modified Binaries**: TEE measurement detects changes
4. **Result Manipulation**: ZK proof ensures correctness
5. **Replay Attacks**: Timestamp and nonce in attestation

**Limitations**:
- Does not protect against physical attacks (requires physical security)
- Does not prevent provider from running multiple VMs (requires resource monitoring)
- Cannot detect time-sharing without continuous monitoring

---

## Troubleshooting

### SGX Issues

```bash
# SGX not working
# 1. Check BIOS settings
# 2. Update microcode
sudo apt-get install intel-microcode

# 3. Reload SGX driver
sudo modprobe -r intel_sgx
sudo modprobe intel_sgx

# 4. Restart AESM service
sudo systemctl restart aesmd
```

### SEV-SNP Issues

```bash
# SEV not working
# 1. Check kernel support
uname -r  # Should be 5.19+

# 2. Check module parameters
cat /sys/module/kvm_amd/parameters/sev
cat /sys/module/kvm_amd/parameters/sev_snp

# 3. Enable in kernel
echo "options kvm_amd sev=1 sev_snp=1" | sudo tee /etc/modprobe.d/kvm_amd.conf
sudo update-initramfs -u
```

---

## References

- [Intel SGX Developer Guide](https://software.intel.com/sgx)
- [Intel SGX DCAP Documentation](https://www.intel.com/content/www/us/en/developer/tools/software-guard-extensions/attestation-services.html)
- [AMD SEV-SNP Whitepaper](https://www.amd.com/content/dam/amd/en/documents/developer/lss-snp-attestation.pdf)
- [Gramine Documentation](https://gramine.readthedocs.io/)
- [RISC Zero](https://www.risczero.com/)
- [SP1 zkVM](https://succinctlabs.github.io/sp1/)
- [ZKProof Standards](https://zkproof.org/)
