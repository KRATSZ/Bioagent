import sys
import json
import traceback


def main() -> int:
    print(f"[env] python={sys.version.split()[0]}")
    try:
        import cfm_id  # type: ignore
    except Exception as e:
        print("[cfm-id] import failed:", e)
        print("[hint] pip install cfm-id")
        return 1

    ver = getattr(cfm_id, "__version__", "unknown")
    print(f"[cfm-id] version={ver}")

    smiles = "CC(=O)O"  # acetic acid
    adduct = "[M+H]+"
    energies = [10, 20, 40]
    charge = 1

    # Try modern convenience API first
    try:
        if hasattr(cfm_id, "predict_spectrum"):
            print("[cfm-id] using predict_spectrum(...) API")
            pred = cfm_id.predict_spectrum(smiles=smiles, adduct=adduct, energies=energies, charge=charge)  # type: ignore
            # Compact preview
            try:
                text = json.dumps(pred)[:500]
            except Exception:
                text = str(pred)[:500]
            print("[ok] spectrum preview:", text)
            return 0
    except Exception:
        print("[warn] predict_spectrum failed:\n" + traceback.format_exc())

    # Try class-based API
    try:
        if hasattr(cfm_id, "CfmId"):
            print("[cfm-id] using CfmId().predict(...) API")
            C = getattr(cfm_id, "CfmId")
            try:
                inst = C()  # if this requires model path, it will raise
            except TypeError as te:
                print("[info] CfmId() requires arguments:", te)
                print("[hint] consult cfm-id docs for model path / weights setup")
                return 2
            out = inst.predict(smiles)  # type: ignore
            try:
                text = json.dumps(out)[:500]
            except Exception:
                text = str(out)[:500]
            print("[ok] spectrum preview:", text)
            return 0
    except Exception:
        print("[warn] CfmId().predict failed:\n" + traceback.format_exc())

    print("[fail] cfm-id loaded but no known API worked. Check package version and documentation.")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())





