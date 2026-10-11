"""Emit every normalized inventory set reference in deterministic order."""


def equipment_sets_wurst(definitions, ws):
    lines = []
    pieces = {row['id']: row for row in definitions['equipmentSetPieces']}
    for index, row in enumerate(definitions['equipmentSets']):
        name = f'equipmentSet{index}'
        lines += [f'\tlet {name}=new EquipmentSet("{ws(row["id"])}")',
                  f'\t{name}.allowDuplicatePieces={str(row["allowDuplicatePieces"]).lower()}']
        for p, piece_id in enumerate(row['pieceIds']):
            piece = pieces[piece_id]
            variable = f'{name}Piece{p}'
            lines.append(f'\tlet {variable}=new EquipmentSetPiece("{ws(piece_id)}")')
            for item_id in sorted(piece['itemTypeIds']):
                lines.append(f'\t{variable}.addItem("{ws(item_id)}")')
            for slot_id in sorted(piece.get('equipmentSlotTypes', [])):
                lines.append(f'\t{variable}.addSlot("{ws(slot_id)}")')
            lines.append(f'\t{name}.addPiece({variable})')
        for t, tier in enumerate(row['thresholds']):
            variable = f'{name}Tier{t}'
            lines.append(f'\tlet {variable}=new EquipmentSetThreshold("{ws(tier["id"])}",{tier["pieceCount"]},"{tier["tierPolicy"]}")')
            # Effect order is authored order, also used by the headless resolver.
            for effect_id in tier['effectIds']:
                lines.append(f'\t{variable}.addEffect("{ws(effect_id)}")')
            for target in sorted(tier['replacesThresholdIds']):
                lines.append(f'\t{variable}.addReplacement("{ws(target)}")')
            lines.append(f'\t{name}.addThreshold({variable})')
        lines.append(f'\truntime.inventory.registerSet({name})')
    return lines
